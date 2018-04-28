"""Code for resolving requirements into concrete versions."""
from typing import List, Optional, Iterable, Set
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
        self.candidates = {}

    async def set_candidates(
            self,
            package_types: List[PackageType],
            sources: List[str],
            session: ClientSession,
    ) -> None:
        if self.info not in candidate_info_cache:
            source, base_metadata = await get_source_and_base_metadata(sources, session, self.info.name)

            candidate_info_cache[self.info] = []
            for version_str, distributions in base_metadata['releases'].items():
                try:
                    version = Version(version_str)
                except InvalidVersion:
                    logger.info('Invalid version for %r: %s', self.info, version_str)
                    continue  # Skip any candidate without a valid version.

                if self.info.specifier and not self.info.specifier.contains(version):
                    continue
                for distribution in distributions:
                    package_type = PackageType[distribution['packagetype']]

                    if package_type.name.startswith('bdist'):
                        filename = distribution['filename']
                        pep425_tag = get_pep425_tag(filename)
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
            self.candidates[candidate_info] = Candidate(candidate_info, self)


class Candidate:
    def __init__(self, info: CandidateInfo, requirement: Requirement):
        self.info = info
        self.requirement = requirement
        self.live = False
        self.requirements = {}

    async def set_requirements(
            self,
            python_version: str,
            extra: str,
            session: ClientSession,
    ):
        if self.info not in requirement_info_cache:
            if self.info.package_type == PackageType.sdist:
                requirement_infos = await get_sdist_requirements(session, self.info)
            else:
                metadata = await get_version_metadata(self.info.source, session, self.info.name, self.info.version)
                requires_dist = metadata['info']['requires_dist']
                if requires_dist is not None:
                    requirement_infos = parse_requires_dist(requires_dist)
                else:
                    requirement_infos = await get_bdist_wheel_requirements(session, self.info)

            requirement_info_cache[self.info] = requirement_infos

        for requirement_info in requirement_info_cache[self.info]:
            environment = {
                'python_version': python_version,
                'extra': extra,
            }
            if requirement_info.marker and not requirement_info.marker.evaluate(environment=environment):
                logger.debug('Skipping %r, marker does not match %r.', requirement_info, environment)
                continue

            requirement = Requirement(requirement_info, self.requirement)

            parents = [requirement]
            while parents[-1].parent is not None:
                parents.append(parents[-1].parent)
                if parents[-1].info.name == requirement.info.name:
                    raise CircularDependencyError([r.info.name for r in parents])

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
        python_version: str,
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
            live_candidate_infos = {c.info for c in live_candidates}
            assert len(live_candidate_infos) == 1
            live_candidate_info = list(live_candidate_infos)[0]
            if requirement.info.specifier is None or requirement.info.specifier.contains(live_candidate_info.version):
                logger.debug('Existing %r satisfies new %r.', live_candidate_info, requirement.info)
                candidate_info = live_candidate_info
            else:
                logger.debug('Existing %r does not satisfy new %r, attempting to resolve.',
                              live_candidate_info, requirement)
                specifier = requirement.info.specifier
                for s in _iter_live_specifiers(base_requirements, requirement.info.name):
                    specifier &= s

                candidate_infos = [c for c in requirement.candidates if specifier.contains(c.version)]
                if not candidate_infos:
                    # FIXME: handle single-pass failures
                    raise Exception(f'Single pass failed on {requirement.info} (rejected existing {live_candidate_info})')

                candidate_info = sorted(candidate_infos, reverse=True)[0]

                # Kill the previously live candidates and switch to the new live candidate.
                for live_candidate in live_candidates:
                    live_candidate.live = False
                    new_candidate = live_candidate.requirement.candidates[candidate_info]
                    new_candidate.live = True
                    # Almost all from cache
                    await new_candidate.set_requirements(
                        python_version=python_version,
                        extra=new_candidate.requirement.info.extra,
                        session=session,
                    )
                    await _resolve_requirement_list(
                        package_types=package_types,
                        python_version=python_version,
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
        await candidate.set_requirements(
            python_version=python_version,
            extra=requirement.info.extra,
            session=session,
        )
        await _resolve_requirement_list(
            package_types=package_types,
            python_version=python_version,
            sources=sources,
            session=session,
            base_requirements=base_requirements,
            requirements=list(candidate.requirements.values()),
        )


async def resolve_requirements_list(
        package_types: List[PackageType],
        python_version: str,
        sources: List[str],
        requirements: List[Requirement],
) -> None:
    connector = TCPConnector(limit=10)
    async with ClientSession(connector=connector) as session:
        await _resolve_requirement_list(
            package_types=package_types,
            python_version=python_version,
            sources=sources,
            session=session,
            base_requirements=requirements,
            requirements=requirements,
        )


def _candidate_info_topo_sort(requirements: Iterable[Requirement], seen: Set[CandidateInfo]) -> Iterable[CandidateInfo]:
    for requirement in requirements:
        for candidate in requirement.candidates.values():
            if candidate.live and candidate.info not in seen:
                seen.add(candidate.info)
                yield from _candidate_info_topo_sort(candidate.requirements.values(), seen)
                yield candidate.info


def candidate_info_topo_sort(requirements: List[Requirement]) -> List[CandidateInfo]:
    return list(_candidate_info_topo_sort(requirements, set()))
