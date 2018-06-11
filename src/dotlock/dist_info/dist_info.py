from collections import namedtuple
from enum import IntEnum, auto
from sqlite3 import Connection
from typing import List
import logging

from aiohttp import ClientSession
from packaging.requirements import Requirement as PackagingRequirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from dotlock.exceptions import NoMatchingCandidateError
from dotlock.markers import Marker


logger = logging.getLogger(__name__)


class PackageType(IntEnum):
    bdist_wininst = auto()
    bdist_msi = auto()
    bdist_egg = auto()
    sdist = auto()
    bdist_rpm = auto()
    bdist_wheel = auto()


class RequirementInfo(namedtuple(
        '_RequirementInfo',
        ('name', 'specifier', 'extras', 'marker'),
    )):
    @classmethod
    def from_specifier_str(cls, name, specifier_str):
        return RequirementInfo(
            name=name,
            specifier=SpecifierSet(specifier_str) if specifier_str != '*' else None,
            extras=tuple(),
            marker=None,
        )

    def __str__(self):
        result = self.name
        if self.extras:
            extras = ','.join(self.extras)
            result += f'[{extras}]'
        specifier_str = str(self.specifier) if self.specifier else '*'
        if self.marker:
            specifier_str += f'; {self.marker}'
        if specifier_str:
            result += f' ({specifier_str})'
        return result

    async def get_candidate_infos(
            self,
            package_types: List[PackageType],
            sources: List[str],
            connection: Connection,
            session: ClientSession,
            update: bool,
    ):
        from dotlock.dist_info.caching import get_cached_candidate_infos, set_cached_candidate_infos
        from dotlock.dist_info.package_indices import get_candidate_infos

        candidate_infos = None
        if not update:
            candidate_infos = get_cached_candidate_infos(connection, self.name)

        if candidate_infos is None:
            candidate_infos = await get_candidate_infos(package_types, sources, session, self.name)
            set_cached_candidate_infos(connection, candidate_infos)

        candidate_infos = [
            c for c in candidate_infos
            if self.specifier is None or self.specifier.contains(c.version)
        ]
        if not candidate_infos:
            raise NoMatchingCandidateError(self)

        return candidate_infos


class CandidateInfo(namedtuple(
        '_CandidateInfo',
        ('name', 'version', 'package_type', 'source', 'url', 'sha256')
    )):
    async def get_requirement_infos(self, connection: Connection, session: ClientSession):
        from dotlock.dist_info.wheel_handling import get_bdist_wheel_requirements
        from dotlock.dist_info.caching import get_cached_requirement_infos, set_cached_requirement_infos
        from dotlock.dist_info.package_indices import get_requirment_infos
        from dotlock.dist_info.sdist_handling import get_sdist_requirements

        requirement_infos = get_cached_requirement_infos(connection, self)
        if requirement_infos is None:
            if self.package_type == PackageType.sdist:
                # Indices do not list dependencies for sdists; they must be downloaded.
                requirement_infos = await get_sdist_requirements(session, self)
            elif self.package_type == PackageType.bdist_wheel:
                # PyPI MAY list dependencies for bdists if using the JSON API.
                requirement_infos = await get_requirment_infos(session, self)
                if requirement_infos is None:
                    # If the dependencies are null, assume the index just doesn't know about them.
                    requirement_infos = await get_bdist_wheel_requirements(session, self)
            else:
                raise Exception(f'Unsupported package type {self.package_type.name}')

            set_cached_requirement_infos(connection, self, requirement_infos)

        return requirement_infos


def parse_requires_dist(requirement_lines: List[str]) -> List[RequirementInfo]:
    requirements = []
    for line in requirement_lines:
        r = PackagingRequirement(line)
        marker = Marker(str(r.marker)) if r.marker else None  # Cast to our Marker subclass
        requirements.append(
            RequirementInfo(canonicalize_name(r.name), r.specifier, tuple(r.extras), marker)
        )

    return requirements
