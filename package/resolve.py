"""Code for resolving requirements into concrete versions."""
from collections import namedtuple
from typing import List, Optional, Iterable
import asyncio
import logging
import re

from aiohttp import ClientSession
from packaging.utils import canonicalize_name
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion
from packaging.markers import Marker

from package.api_requests import get_source_and_base_metadata, get_version_metadata
from package.exceptions import NoMatchingCandidateError, CircularDependencyError


logging.getLogger().setLevel(logging.DEBUG)


class RequirementInfo(namedtuple(
        '_RequirementInfo',
        ('name', 'specifier', 'marker'),
    )):
    def __str__(self):
        specifier_str = str(self.specifier) if self.specifier else '*'
        if self.marker:
            specifier_str += f'; {self.marker}'
        if specifier_str:
            return f'{self.name} ({specifier_str})'
        return self.name


CandidateInfo = namedtuple(
    'CandidateInfo',
    ('name', 'version', 'package_type', 'python_version', 'source', 'sha256')
)


requirement_info_cache = {}
candidate_info_cache = {}


class Requirement:
    def __init__(self, info: RequirementInfo, parent: Optional['Requirement']):
        self.info = info
        self.parent = parent
        self.candidates = {}

    async def set_candidates(
            self,
            package_types: List[str],
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
                    logging.warning('Invalid version for %r: %s', self.info, version_str)
                    continue  # Skip any candidate without a valid version.

                if self.info.specifier and not self.info.specifier.contains(version):
                    continue
                for distribution in distributions:
                    if distribution['packagetype'] in package_types:
                        sha256 = distribution['digests']['sha256']
                        candidate_info_cache[self.info].append(CandidateInfo(
                            name=self.info.name,
                            version=version,
                            package_type=distribution['packagetype'],
                            python_version=distribution['python_version'],
                            source=source,
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
            metadata = await get_version_metadata(self.info.source, session, self.info.name, self.info.version)

            requirement_info_cache[self.info] = parse_requires_dist(metadata['info']['requires_dist'])

        for requirement_info in requirement_info_cache[self.info]:
            if requirement_info.marker and not requirement_info.marker.evaluate(environment={
                'python_version': python_version,
                'extra': extra,
            }):
                logging.debug('Skipping %r because marker does not match environment.', requirement_info)
                continue

            requirement = Requirement(requirement_info, self.requirement)

            parents = [requirement]
            while parents[-1].parent is not None:
                parents.append(parents[-1].parent)
                if parents[-1].info.name == requirement.info.name:
                    raise CircularDependencyError([r.info.name for r in parents])

            self.requirements[requirement_info] = requirement


def parse_requires_dist(requirement_lines: Optional[List[str]]) -> List[RequirementInfo]:
    if not requirement_lines:
        return []

    requirements = []
    for line in requirement_lines:
        if ';' in line:
            line, marker = line.split(';')
            marker = Marker(marker.lstrip())
        else:
            marker = None

        specifier_match = re.match(r'(?P<name>[a-zA-Z\-_0-9]+) \((?P<specifier>.*)\)', line)
        if specifier_match:
            name = canonicalize_name(specifier_match.group('name'))
            specifier = SpecifierSet(specifier_match.group('specifier'))
        else:
            name = canonicalize_name(line)
            specifier = None

        requirements.append(RequirementInfo(name, specifier, marker))

    return requirements


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
        package_types: List[str],
        python_version: str,
        extra: Optional[str],
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

        live_candidates = list(_iter_live_candidates(base_requirements, requirement.info.name))
        if live_candidates:
            live_candidate_infos = {c.info for c in live_candidates}
            assert len(live_candidate_infos) == 1
            live_candidate_info = list(live_candidate_infos)[0]
            if requirement.info.specifier.contains(live_candidate_info.version):
                logging.debug('Existing %r satisfies new %r.', live_candidate_info, requirement.info)
                candidate_info = live_candidate_info
            else:
                logging.debug('Existing %r does not satisfy new %r, attempting to resolve.',
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
                        extra=extra,
                        session=session,
                    )
                    await _resolve_requirement_list(
                        package_types=package_types,
                        python_version=python_version,
                        extra=extra,
                        sources=sources,
                        session=session,
                        base_requirements=base_requirements,
                        requirements=list(new_candidate.requirements.values()),
                    )
        else:
            logging.debug('New package %s discovered.', requirement.info.name)
            candidate_info = sorted(requirement.candidates, reverse=True)[0]

        candidate = requirement.candidates[candidate_info]
        candidate.live = True
        await candidate.set_requirements(
            python_version=python_version,
            extra=extra,
            session=session,
        )
        await _resolve_requirement_list(
            package_types=package_types,
            python_version=python_version,
            extra=extra,
            sources=sources,
            session=session,
            base_requirements=base_requirements,
            requirements=list(candidate.requirements.values()),
        )


async def resolve_requirements_list(
        package_types: List[str],
        python_version: str,
        extra: str,
        sources: List[str],
        requirements: List[Requirement],
) -> None:
    async with ClientSession() as session:
        await _resolve_requirement_list(
            package_types=package_types,
            python_version=python_version,
            extra=extra,
            sources=sources,
            session=session,
            base_requirements=requirements,
            requirements=requirements,
        )
