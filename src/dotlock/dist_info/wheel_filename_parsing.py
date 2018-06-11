from typing import Optional, Tuple
import re

from packaging.version import Version, InvalidVersion

from dotlock._vendored.pep425tags import get_supported


# Regex for parsing wheel filenames per https://www.python.org/dev/peps/pep-0427/#file-name-convention
# Copied from https://github.com/pypa/wheel/blob/8004cbe8dc8be834a40717e3d943af3cc28938cd/wheel/install.py
_WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<ver>\d.*?))(-(?P<build>\d.*?))?
     -(?P<pyver>[a-z].+?)-(?P<abi>.+?)-(?P<plat>.+?)(\.whl|\.dist-info)$""",
    re.VERBOSE)


def get_wheel_version(filename: str) -> Version:
    match = _WHEEL_INFO_RE.match(filename)
    if match:
        return Version(match.group('ver'))
    raise InvalidVersion(filename)


def get_pep425_tag(filename: str) -> Optional[Tuple[str, str, str]]:
    match = _WHEEL_INFO_RE.match(filename)
    if match:
        return (match.group('pyver'), match.group('abi'), match.group('plat'))
    return None


def is_supported(filename: str) -> bool:
    # Per PEP 425, bdist filename encodes what environments the distribution supports.
    pep425_tag = get_pep425_tag(filename)
    # Some bdists don't follow PEP 425 and right now we just assume those are universal.
    if pep425_tag is None:
        return True
    return pep425_tag in get_supported()
