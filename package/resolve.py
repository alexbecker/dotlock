"""Code for parsing package.json files."""
from typing import Dict, List, Optional, Set
from functools import total_ordering
import re

from aiohttp import ClientSession
from packaging.utils import canonicalize_name
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from packaging.markers import Marker

from package.api_requests import get_source_and_base_metadata, get_version_metadata
from package.exceptions import NoMatchingCandidateError, CircularDependencyError


class Requirement:
    def __init__(self, name: str, specifier: Optional[str], marker: Optional[str]):
        self.name = canonicalize_name(name)
        self.specifier = SpecifierSet(specifier) if specifier else None
        self.marker = Marker(marker) if marker else None

    def __repr__(self):
        specifier_str = str(self.specifier) if self.specifier else '*'
        if self.marker:
            specifier_str += f' ;{self.marker}'
        return f'<Requirement {self.name}: "{specifier_str}">'


@total_ordering
class Candidate:
    def __init__(
            self, name: str, version: Version, package_type: str,
            python_version: str, source: str, sha256: str,
    ):
        self.name = canonicalize_name(name)
        self.version = version
        self.package_type = package_type
        self.python_version = python_version
        self.source = source
        self.sha256 = sha256

    def __repr__(self):
        return f'<Candidate {self.name}: "{self.version}">'

    def __hash__(self):
        return hash(self.sha256)

    def __lt__(self, other):
        if not isinstance(other, Candidate):
            raise TypeError()
        if self.name != other.name:
            return self.name < other.name
        return self.version < other.version


def parse_requires_dist(requirement_lines: Optional[List[str]]) -> List[Requirement]:
    if not requirement_lines:
        return []

    requirements = []
    for line in requirement_lines:
        if ';' in line:
            line, marker = line.split(';')
            marker = marker.lstrip()
        else:
            marker = None

        specifier_match = re.match(r'(?P<name>[a-zA-Z\-_0-9]+) \((?P<specifier>.*)\)', line)
        if specifier_match:
            name = specifier_match.group('name')
            specifier = specifier_match.group('specifier')
        else:
            name = line
            specifier = None

        requirements.append(Requirement(name, specifier, marker))

    return requirements


async def _get_top_candidate_tree(
        package_types: str,
        python_version: str,
        sources: List[str],
        requirements: List[Requirement],
        parents: List[Requirement],
        candidates_seen: Dict[str, Candidate],
) -> dict:
    candidate_tree = {}

    async with ClientSession() as session:
        for requirement in requirements:
            if requirement.name in parents:
                raise CircularDependencyError(parents + [requirement])

            if requirement.marker:
                continue    # FIXME: handle markers

            existing_candidate = candidates_seen.get(requirement.name)
            if existing_candidate:
                if requirement.specifier.contains(existing_candidate.version):
                    continue
                else:
                    # FIXME: handle single-pass failures
                    raise Exception(f'Single pass failed on {requirement} (rejected exisiting {existing_candidate})')

            print(requirement)
            source, base_metadata = await get_source_and_base_metadata(sources, session, requirement.name)

            candidates = []
            for version_str, distributions in base_metadata['releases'].items():
                version = Version(version_str)
                if requirement.specifier and not requirement.specifier.contains(version):
                    continue
                for distribution in distributions:
                    if (distribution['packagetype'] in package_types and
                            distribution['python_version'] in [python_version, "source", "any", "py2.py3"]):
                        sha256 = distribution['digests']['sha256']
                        candidates.append(Candidate(
                            name=requirement.name,
                            version=version,
                            package_type=distribution['packagetype'],
                            python_version=distribution['python_version'],
                            source=source,
                            sha256=sha256,
                        ))

            if not candidates:
                raise NoMatchingCandidateError(requirement.name, requirement.specifier)

            candidate_tree[requirement] = {}

            candidates = sorted(candidates, reverse=True)
            candidate = candidates[0]
            candidates_seen[candidate.name] = candidate
            if candidate.version == Version(base_metadata['info']['version']):
                metadata = base_metadata
            else:
                metadata = await get_version_metadata(source, session, candidate.name, candidate.version)

            candidate_requirements = parse_requires_dist(metadata['info']['requires_dist'])
            candidate_tree[requirement][candidate] = await _get_top_candidate_tree(
                package_types=package_types,
                python_version=python_version,
                sources=sources,
                requirements=candidate_requirements,
                parents=parents + [requirement],
                candidates_seen=candidates_seen,
            )

    return candidate_tree


async def get_top_candidate_tree(
        package_types: str,
        python_version: str,
        sources: List[str],
        requirements: List[Requirement],
) -> dict:
    return await _get_top_candidate_tree(
        package_types=package_types,
        python_version=python_version,
        sources=sources,
        requirements=requirements,
        parents=[],
        candidates_seen={},
    )


def flatten_candidate_tree(candidate_tree: Dict[Requirement, dict]) -> List[Candidate]:
    flat = []
    for requirement, candidates in candidate_tree.items():
        for candidate, requirements in candidates.items():
            flat.append(candidate)
            flat.extend(flatten_candidate_tree(requirements))
    return flat
