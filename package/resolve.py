"""Code for resolving requirements into concrete versions."""
from typing import List, Optional, Iterable, Set, Dict
import logging
import asyncio

from aiohttp import ClientSession, TCPConnector
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion

from package.api_requests import get_source_and_base_metadata, get_version_metadata
from package.bdist_wheel_handling import get_bdist_wheel_requirements
from package.dist_info_parsing import PackageType, RequirementInfo, CandidateInfo, get_pep425_tag, parse_requires_dist
from package.exceptions import NoMatchingCandidateError, CircularDependencyError
from package.pep425tags import get_supported
from package.sdist_handling import get_sdist_requirements


logger = logging.getLogger(__name__)

requirement_info_cache = {}
candidate_info_cache = {}


class Requirement:
    def __init__(self, info: RequirementInfo, parent: Optional['Requirement']):
        self.info = info
        self.parent = parent
        # Requirements and Candidates form an alternating tree.
        # Each Requirement has a collection of Candidates, which in turn have Requirements.
        # These are recursively populated by resolve_requirement_list.
        self.candidates: Dict[CandidateInfo: Candidate] = {}

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
            session: ClientSession,
    ) -> None:
        """
        Populates self.candidates. Does not populate requirements for these candidates.

        Args:
            package_types: Allowed PackageTypes for candidates.
            sources: Base URLs for PyPI-like package repositories.
            session: Async session to use for HTTP requests.
        """
        if self.info not in candidate_info_cache:
            source, base_metadata = await get_source_and_base_metadata(sources, session, self.info.name)

            candidate_info_cache[self.info] = []
            for version_str, distributions in base_metadata['releases'].items():
                try:
                    version = Version(version_str)
                except InvalidVersion:
                    logger.info('Invalid version for %r: %s', self.info, version_str)
                    continue  # Skip candidates without a valid version.

                if self.info.specifier and not self.info.specifier.contains(version):
                    continue  # Skip candidates whose versions don't satisfy the requirement.

                for distribution in distributions:
                    package_type = PackageType[distribution['packagetype']]

                    if package_type.name.startswith('bdist'):
                        # Per PEP 425, bdist filename encodes what environments the distribution supports.
                        filename = distribution['filename']
                        pep425_tag = get_pep425_tag(filename)
                        # Some bdists don't follow PEP 425 and right now we just assume those are universal.
                        if pep425_tag is not None and pep425_tag not in get_supported():
                            logger.debug('Skipping unsupported bdist %s', filename)
                            continue

                    if package_type not in package_types:
                        logger.debug('Skipping package type %s for %s', package_type.name, self.info.name)
                        continue

                    sha256 = distribution['digests']['sha256']
                    candidate_info_cache[self.info].append(CandidateInfo(
                        name=self.info.name,
                        version=version,
                        package_type=package_type,
                        source=source,
                        url=distribution['url'],
                        sha256=sha256,
                    ))

            if not candidate_info_cache[self.info]:
                raise NoMatchingCandidateError(self.info)

        for candidate_info in candidate_info_cache[self.info]:
            extras = {self.info.extra} if self.info.extra else set()
            self.candidates[candidate_info] = Candidate(candidate_info, self, extras)


class Candidate:
    def __init__(self, info: CandidateInfo, requirement: Requirement, extras: Set[str]):
        self.info = info
        self.requirement = requirement
        # During resolution, we may discover other Requirements which force us to install
        # more extras for an already existing Candidate, hence this set is mutable.
        self.extras = extras
        # The live flag lets us populate a Requirement with all Candidates, while only having one "in-use" candidate.
        # Which candidate is live for a given Requirement may change if we are forced to backtrack during resolution.
        self.live = False
        self.requirements: Dict[RequirementInfo: Requirement] = {}

    async def set_requirements(self, session: ClientSession):
        """
        Populates self.requirements. Does not populate candidates for these requirements.

        Args:
            session: Async session to use for HTTP requests.
        """
        if self.info not in requirement_info_cache:
            if self.info.package_type == PackageType.sdist:
                # PyPI does not list dependencies for sdists; they must be downloaded.
                requirement_infos = await get_sdist_requirements(session, self.info)
            else:
                # PyPI MAY list dependencies for bdists.
                metadata = await get_version_metadata(self.info.source, session, self.info.name, self.info.version)
                requires_dist = metadata['info']['requires_dist']
                if requires_dist is not None:
                    requirement_infos = parse_requires_dist(requires_dist)
                else:
                    # If the dependencies are null, assume PyPI just doesn't know about them.
                    requirement_infos = await get_bdist_wheel_requirements(session, self)

            requirement_info_cache[self.info] = requirement_infos

        for requirement_info in requirement_info_cache[self.info]:
            # Skip any requirements that do not apply to the current environment
            # or are for extras we do not want for this candidate.
            if requirement_info.marker:
                # Marker.evaluate requires exactly 1 'extra', so we iterate over self.extras
                # or just use None if we do not want any extras.
                environments = [{'extra': extra} for extra in self.extras] if self.extras else [{'extra': None}]
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
        session: ClientSession,
        base_requirements: List[Requirement],
        requirements: List[Requirement],
) -> None:
    await asyncio.gather(*[
        requirement.set_candidates(package_types, sources, session)
        for requirement in requirements
    ])

    for requirement in requirements:
        logger.debug('Resolving %r', requirement.info)

        live_candidates = list(_iter_live_candidates(base_requirements, requirement.info.name))
        if live_candidates:
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
                    if requirement.info.extra:
                        new_candidate.extras.add(requirement.info.extra)
                    # Re-resolve this branch of the tree since we selected a new candidate.
                    # Should be fast since the caches will be hot.
                    await new_candidate.set_requirements(session=session)
                    await _resolve_requirement_list(
                        package_types=package_types,
                        sources=sources,
                        session=session,
                        base_requirements=base_requirements,
                        requirements=list(new_candidate.requirements.values()),
                    )
        else:
            logger.debug('New package %s discovered.', requirement.info.name)
            candidate_info = sorted(requirement.candidates, reverse=True)[0]

        candidate = requirement.candidates[candidate_info]
        candidate.live = True
        if requirement.info.extra:
            candidate.extras.add(requirement.info.extra)
        await candidate.set_requirements(session=session)
        await _resolve_requirement_list(
            package_types=package_types,
            sources=sources,
            session=session,
            base_requirements=base_requirements,
            requirements=list(candidate.requirements.values()),
        )


async def resolve_requirements_list(
        package_types: List[PackageType],
        sources: List[str],
        requirements: List[Requirement],
) -> None:
    """
    Populates requirements.candidates, recursively, selecting a unique Candidate up to name.

    Args:
        package_types: Allowed PackageTypes for candidates.
        sources: Base URLs for PyPI-like package repositories.
        requirements: Unpopulated list of requirements, e.g. just parsed from package.json.
    """
    # Too many connections results in '(104) Connection reset by peer' errors.
    connector = TCPConnector(limit=10)  # 10 is arbitrary; could probably be raised.
    async with ClientSession(connector=connector) as session:
        await _resolve_requirement_list(
            package_types=package_types,
            sources=sources,
            session=session,
            base_requirements=requirements,
            requirements=requirements,
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


def candidate_topo_sort(requirements: List[Requirement]) -> List[Candidate]:
    """
    Args:
        requirements: A fully resolved list of requirements.

    Returns: A list of Candidates satisfying all Requirements (recursively), sorted
             such that if Candidate A depends on Candidate B, B will precede A.
    """
    return list(_candidate_topo_sort(requirements, set()))
