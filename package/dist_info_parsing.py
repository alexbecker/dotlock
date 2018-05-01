from collections import namedtuple
from enum import IntEnum, auto
from typing import List
import re

from packaging.requirements import Requirement as PackagingRequirement
from packaging.utils import canonicalize_name


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


CandidateInfo = namedtuple(
    'CandidateInfo',
    ('name', 'version', 'package_type', 'source', 'url', 'sha256')
)


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
        requirements.append(
            RequirementInfo(canonicalize_name(r.name), r.specifier, extra, r.marker)
        )

    return requirements
