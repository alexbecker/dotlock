import pytest

from dotlock.dist_info.dist_info import RequirementInfo, SpecifierSet, SpecifierType


def test_from_specifier_str_wildcard():
    assert RequirementInfo.from_specifier_str('package', '*') == RequirementInfo(
        name='package',
        specifier_type=SpecifierType.version,
        specifier=SpecifierSet(),
        extras=tuple(),
        marker=None,
    )


def test_from_specifier_str_version():
    assert RequirementInfo.from_specifier_str('package', '>=2.3.4,<=3.0.0') == RequirementInfo(
        name='package',
        specifier_type=SpecifierType.version,
        specifier=SpecifierSet('>=2.3.4,<=3.0.0'),
        extras=tuple(),
        marker=None,
    )


def test_from_specifier_str_vcs():
    assert RequirementInfo.from_specifier_str('package', 'git+git://github.com/python/package') == RequirementInfo(
        name='package',
        specifier_type=SpecifierType.vcs,
        specifier='git+git://github.com/python/package',
        extras=tuple(),
        marker=None,
    )


@pytest.mark.parametrize('path', [
    '.', './package', '/home/foo/package',
])
def test_from_specifier_str_path(path):
    assert RequirementInfo.from_specifier_str('package', path) == RequirementInfo(
        name='package',
        specifier_type=SpecifierType.path,
        specifier=path,
        extras=tuple(),
        marker=None,
    )
