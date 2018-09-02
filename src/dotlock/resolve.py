"""Code for resolving requirements into concrete versions."""
from sqlite3 import Connection
from typing import List, Optional, Iterable, Set, Dict, Tuple
import logging
import asyncio

from aiohttp import ClientSession, TCPConnector
from packaging.specifiers import SpecifierSet

from dotlock.dist_info.caching import connect_to_cache
from dotlock.dist_info.dist_info import PackageType, RequirementInfo, CandidateInfo
from dotlock.exceptions import CircularDependencyError


logger = logging.getLogger(__name__)


class Requirement:
    def __init__(self, info: RequirementInfo, parent: Optional['Requirement']) -> None:
        self.info = info
        self.parent = parent
        # Requirements and Candidates form an alternating tree.
        # Each Requirement has a collection of Candidates, which in turn have Requirements.
        # These are recursively populated by resolve_requirement_list.
        self.candidates: Dict[CandidateInfo, Candidate] = {}

    def _ancestors(self, ancestors: List['Requirement']) -> List['Requirement']:
        if ancestors and self.info.name == ancestors[0].info.name:
            raise CircularDependencyError(ancestors)

        ancestors.append(self)
        if self.parent:
            self.parent._ancestors(ancestors)

        return ancestors

    def ancestors(self) -> List['Requirement']:
        """Returns [..., parent.parent.self, parent.self, self]"""
        return self._ancestors([])

    async def set_candidates(
            self,
            package_types: List[PackageType],
            sources: List[str],
            connection: Connection,
            session: ClientSession,
            update: bool,
    ) -> None:
        """
        Populates self.candidates. Does not populate requirements for these candidates.

        Args:
            package_types: Allowed PackageTypes for candidates.
            sources: Base URLs for PyPI-like package repositories.
            connection: Sqlite3 connection to the cache database.
            session: Async session to use for HTTP requests.
        """
        candidate_infos = await self.info.get_candidate_infos(
            package_types, sources, connection, session, update,
        )
        for candidate_info in candidate_infos:
            extras = set(self.info.extras)
            self.candidates[candidate_info] = Candidate(candidate_info, self, extras)


class Candidate:
    def __init__(self, info: CandidateInfo, requirement: Requirement, extras: Set[str]) -> None:
        self.info = info
        self.requirement = requirement
        # During resolution, we may discover other Requirements which force us to install
        # more extras for an already existing Candidate, hence this set is mutable.
        self.extras = extras
        # The live flag lets us populate a Requirement with all Candidates, while only having one "in-use" candidate.
        # Which candidate is live for a given Requirement may change if we are forced to backtrack during resolution.
        self.live = False
        self.requirements: Dict[RequirementInfo, Requirement] = {}

    async def set_requirements(self, connection: Connection, session: ClientSession) -> None:
        """
        Populates self.requirements. Does not populate candidates for these requirements.

        Args:
            connection: Sqlite3 connection to the cache database.
            session: Async session to use for HTTP requests.
        """
        requirement_infos = await self.info.get_requirement_infos(connection, session)
        for requirement_info in requirement_infos:
            # Skip any requirements that do not apply to the current environment
            # or are for extras we do not want for this candidate.
            if requirement_info.marker:
                # Marker.evaluate requires exactly 1 'extra', so we iterate over self.extras
                # or just use '' if we do not want any extras.
                environments = [{'extra': extra} for extra in self.extras] if self.extras else [{'extra': ''}]
                if not any(
                    requirement_info.marker.evaluate(environment) for environment in environments
                ):
                    logger.debug('Skipping %r, marker does not match environment.', requirement_info)
                    continue

            requirement = Requirement(requirement_info, self.requirement)
            logger.debug('Adding requirement %r from chain %r', requirement_info, [
                r.info.name for r in requirement.ancestors()  # Also checks for circular dependencies.
            ])
            self.requirements[requirement_info] = requirement


def _iter_live_specifiers(base_requirements: Iterable[Requirement], name: str) -> Iterable[SpecifierSet]:
    for requirement in base_requirements:
        if requirement.info.name == name:
            yield requirement.info.specifier
        for candidate in requirement.candidates.values():
            if candidate.live:
                yield from _iter_live_specifiers(candidate.requirements.values(), name)


def _iter_live_candidates(base_requirements: Iterable[Requirement], name: str) -> Iterable[Candidate]:
    for requirement in base_requirements:
        for candidate in requirement.candidates.values():
            if candidate.live:
                if candidate.info.name == name:
                    yield candidate
                yield from _iter_live_candidates(candidate.requirements.values(), name)


async def _resolve_requirement_list(
        package_types: List[PackageType],
        sources: List[str],
        connection: Connection,
        session: ClientSession,
        base_requirements: List[Requirement],
        requirements: List[Requirement],
        update: bool,
) -> None:
    await asyncio.gather(*[
        requirement.set_candidates(package_types, sources, connection, session, update)
        for requirement in requirements
    ])

    for requirement in requirements:
        logger.debug('Resolving %r', requirement.info)

        live_candidates = list(_iter_live_candidates(base_requirements, requirement.info.name))
        if not live_candidates:
            logger.debug('New package %s discovered.', requirement.info.name)
            candidate_info = sorted(requirement.candidates, reverse=True)[0]
        else:
            # Note that all live candidates for a given name will have identical CandidateInfo.
            live_candidate_infos = {c.info for c in live_candidates}
            assert len(live_candidate_infos) == 1
            live_candidate_info = list(live_candidate_infos)[0]

            if requirement.info.specifier is None or requirement.info.specifier.contains(live_candidate_info.version):
                logger.debug('Existing %r satisfies new %r.', live_candidate_info, requirement.info)
                candidate_info = live_candidate_info
            else:
                logger.debug('Existing %r does not satisfy new %r, attempting to resolve.',
                              live_candidate_info, requirement)

                # Filter down to candidates that satisfy all requirements for the current name.
                specifier = requirement.info.specifier
                for s in _iter_live_specifiers(base_requirements, requirement.info.name):
                    specifier &= s
                candidate_infos = [c for c in requirement.candidates if specifier.contains(c.version)]
                if not candidate_infos:
                    # FIXME: handle single-pass failures
                    raise Exception(f'Single pass failed on {requirement.info} (rejected existing {live_candidate_info})')

                # Select a single acceptable candidate, defaulting to the highest version and package_type.
                # TODO: allow different resolution strategies
                candidate_info = sorted(candidate_infos, reverse=True)[0]

                # Update the live candidates for other requirements with the same name.
                for live_candidate in live_candidates:
                    live_candidate.live = False
                    new_candidate = live_candidate.requirement.candidates[candidate_info]
                    new_candidate.live = True
                    # Since we will ultimately only install one copy of Candidate,
                    # all of them need to have the full set of extras.
                    new_candidate.extras.update(requirement.info.extras)
                    # Re-resolve this branch of the tree since we selected a new candidate.
                    # Should be fast since the caches will be hot.
                    await new_candidate.set_requirements(connection=connection, session=session)
                    await _resolve_requirement_list(
                        package_types=package_types,
                        sources=sources,
                        connection=connection,
                        session=session,
                        base_requirements=base_requirements,
                        requirements=list(new_candidate.requirements.values()),
                        update=update,
                    )

        candidate = requirement.candidates[candidate_info]
        candidate.live = True
        candidate.extras.update(requirement.info.extras)
        await candidate.set_requirements(connection=connection, session=session)
        await _resolve_requirement_list(
            package_types=package_types,
            sources=sources,
            connection=connection,
            session=session,
            base_requirements=base_requirements,
            requirements=list(candidate.requirements.values()),
            update=update,
        )


async def resolve_requirements_list(
        package_types: List[PackageType],
        sources: List[str],
        requirements: List[Requirement],
        update: bool,
) -> None:
    """
    Populates requirements.candidates, recursively, selecting a unique Candidate up to name.

    Args:
        package_types: Allowed PackageTypes for candidates.
        sources: Base URLs for PyPI-like package repositories.
        requirements: Unpopulated list of requirements, e.g. just parsed from package.json.
        update: Whether to bypass the cache when finding candidates.
    """
    cache_connection = connect_to_cache()
    # Too many connections results in '(104) Connection reset by peer' errors.
    connector = TCPConnector(limit=10)  # 10 is arbitrary; could probably be raised.
    async with ClientSession(connector=connector) as session:
        await _resolve_requirement_list(
            package_types=package_types,
            sources=sources,
            connection=cache_connection,
            session=session,
            base_requirements=requirements,
            requirements=requirements,
            update=update,
        )


def _candidate_topo_sort(requirements: Iterable[Requirement], seen: Set[str]) -> Iterable[Candidate]:
    for requirement in requirements:
        for candidate in requirement.candidates.values():
            name = candidate.info.name
            if candidate.live and name not in seen:
                seen.add(name)  # OK because Candidates must be uniquely named.
                # Recurse first so that all dependencies are iterated over before candidate.
                yield from _candidate_topo_sort(candidate.requirements.values(), seen)
                yield candidate


def candidate_topo_sort(requirements: Iterable[Requirement]) -> Tuple[Candidate, ...]:
    """
    Args:
        requirements: A fully resolved list of requirements.

    Returns: A list of Candidates satisfying all Requirements (recursively), sorted
             such that if Candidate A depends on Candidate B, B will precede A.
    """
    return tuple(_candidate_topo_sort(requirements, set()))
