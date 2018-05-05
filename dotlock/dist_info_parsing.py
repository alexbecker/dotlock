from collections import namedtuple
from enum import IntEnum, auto
from typing import List
import re
import logging

from aiohttp import ClientSession
from packaging.requirements import Requirement as PackagingRequirement
from packaging.utils import canonicalize_name
from packaging.version import Version, InvalidVersion

from dotlock.api_requests import get_source_and_base_metadata, get_version_metadata
from dotlock.exceptions import NoMatchingCandidateError
from dotlock.markers import Marker
from dotlock.pep425tags import get_supported


logger = logging.getLogger(__name__)

requirement_info_cache = {}
candidate_info_cache = {}


class PackageType(IntEnum):
    bdist_wininst = auto()
    bdist_msi = auto()
    bdist_egg = auto()
    sdist = auto()
    bdist_rpm = auto()
    bdist_wheel = auto()


class RequirementInfo(namedtuple(
        '_RequirementInfo',
        ('name', 'specifier', 'extra', 'marker'),
    )):
    def __str__(self):
        result = self.name
        if self.extra:
            result += f'[{self.extra}]'
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
            session: ClientSession,
    ):
        if self not in candidate_info_cache:
            source, base_metadata = await get_source_and_base_metadata(sources, session, self.name)

            candidate_info_cache[self] = []
            for version_str, distributions in base_metadata['releases'].items():
                try:
                    version = Version(version_str)
                except InvalidVersion:
                    logger.info('Invalid version for %r: %s', self, version_str)
                    continue  # Skip candidates without a valid version.

                if self.specifier and not self.specifier.contains(version):
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
                        logger.debug('Skipping package type %s for %s', package_type.name, self.name)
                        continue

                    sha256 = distribution['digests']['sha256']
                    candidate_info_cache[self].append(CandidateInfo(
                        name=self.name,
                        version=version,
                        package_type=package_type,
                        source=source,
                        url=distribution['url'],
                        sha256=sha256,
                    ))

            if not candidate_info_cache[self]:
                raise NoMatchingCandidateError(self)

        return candidate_info_cache[self]


class CandidateInfo(namedtuple(
        '_CandidateInfo',
        ('name', 'version', 'package_type', 'source', 'url', 'sha256')
    )):
    async def get_requirement_infos(self, session: ClientSession):
        from dotlock.bdist_wheel_handling import get_bdist_wheel_requirements
        from dotlock.sdist_handling import get_sdist_requirements

        if self not in requirement_info_cache:
            if self.package_type == PackageType.sdist:
                # PyPI does not list dependencies for sdists; they must be downloaded.
                requirement_infos = await get_sdist_requirements(session, self)
            else:
                # PyPI MAY list dependencies for bdists.
                metadata = await get_version_metadata(self.source, session, self.name, self.version)
                requires_dist = metadata['info']['requires_dist']
                if requires_dist is not None:
                    requirement_infos = parse_requires_dist(requires_dist)
                else:
                    # If the dependencies are null, assume PyPI just doesn't know about them.
                    requirement_infos = await get_bdist_wheel_requirements(session, self)

            requirement_info_cache[self] = requirement_infos

        return requirement_info_cache[self]


# Regex for parsing wheel filenames per https://www.python.org/dev/peps/pep-0427/#file-name-convention
# Copied from https://github.com/pypa/wheel/blob/8004cbe8dc8be834a40717e3d943af3cc28938cd/wheel/install.py
_WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<ver>\d.*?))(-(?P<build>\d.*?))?
     -(?P<pyver>[a-z].+?)-(?P<abi>.+?)-(?P<plat>.+?)(\.whl|\.dist-info)$""",
    re.VERBOSE)


def get_pep425_tag(filename):
    match = _WHEEL_INFO_RE.match(filename)
    if match:
        return (match.group('pyver'), match.group('abi'), match.group('plat'))


def parse_requires_dist(requirement_lines: List[str]) -> List[RequirementInfo]:
    requirements = []
    for line in requirement_lines:
        r = PackagingRequirement(line)
        extra = list(r.extras)[0] if r.extras else None  # FIXME: handle multiple extras?
        marker = Marker(str(r.marker)) if r.marker else None  # Cast to our Marker subclass
        requirements.append(
            RequirementInfo(canonicalize_name(r.name), r.specifier, extra, marker)
        )

    return requirements
