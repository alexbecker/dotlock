from collections import namedtuple
from enum import Enum, IntEnum, auto
from sqlite3 import Connection
from typing import List
from urllib.parse import urlparse
import logging

from aiohttp import ClientSession
from packaging.requirements import Requirement as PackagingRequirement
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.utils import canonicalize_name
from packaging.version import Version

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
    vcs = auto()
    local = auto()


class SpecifierType(Enum):
    version = auto()
    vcs = auto()
    path = auto()


hash_algorithms = (
    'sha256',
    'sha1',
    'md5',
)


class RequirementInfo(namedtuple(
        '_RequirementInfo',
        ('name', 'specifier_type', 'specifier', 'extras', 'marker'),
    )):
    @classmethod
    def from_specifier_str(cls, name, specifier_str, extras=None, marker=None):
        if specifier_str == '*':
            specifier = SpecifierSet('')
            specifier_type = SpecifierType.version
        else:
            try:
                specifier = SpecifierSet(specifier_str)
                specifier_type = SpecifierType.version
            except InvalidSpecifier:
                parsed_url = urlparse(specifier_str)
                # urlparse doesn't actually fail on invalid URLs, so check this at least has a scheme
                if parsed_url.scheme:
                    specifier = parsed_url.geturl()
                    specifier_type = SpecifierType.vcs
                else:
                    specifier = specifier_str
                    specifier_type = SpecifierType.path

        return cls(
            name=name,
            specifier_type=specifier_type,
            specifier=specifier,
            extras=tuple(extras) if extras else tuple(),
            marker=marker and Marker(marker),
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

        if self.specifier_type == SpecifierType.vcs:
            candidate_infos = [
                CandidateInfo(
                    name=self.name,
                    version=None,
                    package_type=PackageType.vcs,
                    source=None,
                    location=self.specifier,
                    hash_alg=None,  # FIXME
                    hash_val=None,  # FIXME
                )
            ]
        elif self.specifier_type == SpecifierType.path:
            candidate_infos = [
                CandidateInfo(
                    name=self.name,
                    version=None,
                    package_type=PackageType.local,
                    source=None,
                    location=self.specifier,
                    hash_alg=None,  # FIXME
                    hash_val=None,  # FIXME
                )
            ]
        else:
            cached = None
            if not update:
                cached = get_cached_candidate_infos(connection, self.name)

            if cached is None:
                candidate_infos = await get_candidate_infos(package_types, sources, session, self.name)
                set_cached_candidate_infos(connection, candidate_infos)
            else:
                candidate_infos = cached

            candidate_infos = [
                c for c in candidate_infos
                if self.specifier_type != SpecifierType.version or self.specifier.contains(c.version)
            ]
            if not candidate_infos:
                raise NoMatchingCandidateError(self)

        return candidate_infos


class CandidateInfo(namedtuple(
        '_CandidateInfo',
        ('name', 'version', 'package_type', 'source', 'location', 'hash_alg', 'hash_val')
    )):
    @classmethod
    def from_json(cls, data):
        return cls(
            name=data['name'],
            version=data['version'] and Version(data['version']),
            package_type=PackageType[data['package_type']],
            source=data['source'],
            location=data['location'],
            hash_alg=data['hash_alg'],
            hash_val=data['hash_val'],
        )

    def to_json(self):
        return {
            'name': self.name,
            'version': self.version and str(self.version),
            'package_type': self.package_type.name,
            'source': self.source,
            'location': self.location,
            'hash_alg': self.hash_alg,
            'hash_val': self.hash_val,
        }

    async def get_requirement_infos(self, connection: Connection, session: ClientSession):
        from dotlock.dist_info.wheel_handling import get_bdist_wheel_requirements
        from dotlock.dist_info.caching import get_cached_requirement_infos, set_cached_requirement_infos
        from dotlock.dist_info.package_indices import get_requirment_infos
        from dotlock.dist_info.sdist_handling import get_sdist_requirements, get_local_package_requirements
        from dotlock.dist_info.vcs import get_vcs_requirement_infos

        uncachable_types = (PackageType.vcs, PackageType.local)
        if self.package_type not in uncachable_types:
            requirement_infos = get_cached_requirement_infos(connection, self)
            if requirement_infos is not None:
                return requirement_infos

        if self.package_type == PackageType.vcs:
            requirement_infos = await get_vcs_requirement_infos(self)
        elif self.package_type == PackageType.local:
            requirement_infos = get_local_package_requirements(self.name, self.location)
        elif self.package_type == PackageType.sdist:
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
        assert requirement_infos is not None

        if self.package_type not in uncachable_types:
            set_cached_requirement_infos(connection, self, requirement_infos)

        return requirement_infos


def parse_requires_dist(requirement_lines: List[str]) -> List[RequirementInfo]:
    requirements = []
    for line in requirement_lines:
        r = PackagingRequirement(line)
        marker = Marker(str(r.marker)) if r.marker else None  # Cast to our Marker subclass
        requirements.append(
            RequirementInfo(
                name=canonicalize_name(r.name),
                specifier_type=SpecifierType.version,
                specifier=r.specifier,
                extras=tuple(r.extras),
                marker=marker,
            )
        )

    return requirements
