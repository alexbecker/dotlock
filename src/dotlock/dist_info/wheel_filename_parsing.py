from typing import Optional, Tuple
import re

from packaging.version import Version, InvalidVersion

from dotlock.env import pep425tags
from dotlock._vendored.pep425tags import _osx_arch_pat, get_darwin_arches


def get_supported(version, platform, impl, abi, manylinux1, noarch=False):
    """
    Based on get_supported in https://github.com/pypa/pip/blob/10.0.1/src/pip/_internal/pep425tags.py
    but differs in that it accepts full platform specification instead of using the current platform,
    and it expects a version in the form `major.minor`.
    """
    supported = []

    versions = []
    version_info = tuple(int(x) for x in version.split('.'))
    major = version_info[:-1]
    # Support all previous minor Python versions.
    for minor in range(version_info[-1], -1, -1):
        versions.append(''.join(map(str, major + (minor,))))

    abis = [abi]

    abi3s = set()
    import imp
    for suffix in imp.get_suffixes():
        if suffix[0].startswith('.abi'):
            abi3s.add(suffix[0].split('.', 2)[1])

    abis.extend(sorted(list(abi3s)))

    abis.append('none')

    if not noarch:
        arch = platform
        if arch.startswith('macosx'):
            # support macosx-10.6-intel on macosx-10.9-x86_64
            match = _osx_arch_pat.match(arch)
            if match:
                name, major, minor, actual_arch = match.groups()
                tpl = '{}_{}_%i_%s'.format(name, major)
                arches = []
                for m in reversed(range(int(minor) + 1)):
                    for a in get_darwin_arches(int(major), m, actual_arch):
                        arches.append(tpl % (m, a))
            else:
                # arch pattern didn't match (?!)
                arches = [arch]
        # DIFFERS FROM ORIGINAL: support manylinux1 even if platform is specified.
        elif manylinux1:
            arches = [arch.replace('linux', 'manylinux1'), arch]
        else:
            arches = [arch]

        # Current version, current API (built specifically for our Python):
        for abi in abis:
            for arch in arches:
                supported.append(('%s%s' % (impl, versions[0]), abi, arch))

        # abi3 modules compatible with older version of Python
        for version in versions[1:]:
            # abi3 was introduced in Python 3.2
            if version in {'31', '30'}:
                break
            for abi in abi3s:   # empty set if not Python 3
                for arch in arches:
                    supported.append(("%s%s" % (impl, version), abi, arch))

        # Has binaries, does not use the Python API:
        for arch in arches:
            supported.append(('py%s' % (versions[0][0]), 'none', arch))

    # No abi / arch, but requires our implementation:
    supported.append(('%s%s' % (impl, versions[0]), 'none', 'any'))
    # Tagged specifically as being cross-version compatible
    # (with just the major version specified)
    supported.append(('%s%s' % (impl, versions[0][0]), 'none', 'any'))

    # No abi / arch, generic Python
    for i, version in enumerate(versions):
        supported.append(('py%s' % (version,), 'none', 'any'))
        if i == 0:
            supported.append(('py%s' % (version[0]), 'none', 'any'))

    # NOT IN ORIGINAL: support universal wheels
    supported.append(('py2.py3', 'none', 'any'))

    return supported


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
    return pep425_tag in get_supported(**pep425tags)
