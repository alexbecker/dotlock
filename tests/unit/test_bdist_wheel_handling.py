from pathlib import Path

from packaging.specifiers import SpecifierSet

from dotlock.dist_info.dist_info import RequirementInfo, SpecifierType
from dotlock.dist_info.wheel_handling import get_wheel_file_requirements
from dotlock.markers import Marker


def test_get_wheel_file_requirements():
    acme_wheel_file = str(Path(__file__).parent / Path('acme-0.24.0-py2.py3-none-any.whl'))
    requirements = get_wheel_file_requirements(acme_wheel_file)

    assert requirements == [
        RequirementInfo.from_specifier_str('cryptography', '>=0.8'),
        RequirementInfo.from_specifier_str('josepy', '>=1.0.0'),
        RequirementInfo.from_specifier_str('mock', ''),
        RequirementInfo.from_specifier_str('pyopenssl', '>=0.13'),
        RequirementInfo.from_specifier_str('pyrfc3339', ''),
        RequirementInfo.from_specifier_str('pytz', ''),
        RequirementInfo(name='requests', specifier_type=SpecifierType.version, specifier=SpecifierSet('>=2.4.1'),
                        extras=('security',), marker=None),
        RequirementInfo.from_specifier_str('setuptools', ''),
        RequirementInfo(name='six', specifier_type=SpecifierType.version, specifier=SpecifierSet('>=1.9.0'),
                        extras=tuple(), marker=None),
        RequirementInfo(name='pytest', specifier_type=SpecifierType.version, specifier=SpecifierSet(''), extras=tuple(),
                        marker=Marker('extra == "dev"')),
        RequirementInfo(name='pytest-xdist', specifier_type=SpecifierType.version, specifier=SpecifierSet(''),
                        extras=tuple(), marker=Marker('extra == "dev"')),
        RequirementInfo(name='tox', specifier_type=SpecifierType.version, specifier=SpecifierSet(''), extras=tuple(),
                        marker=Marker('extra == "dev"')),
        RequirementInfo(name='sphinx', specifier_type=SpecifierType.version, specifier=SpecifierSet('>=1.0'),
                        extras=tuple(), marker=Marker('extra == "docs"')),
        RequirementInfo(name='sphinx-rtd-theme', specifier_type=SpecifierType.version, specifier=SpecifierSet(''),
                        extras=tuple(), marker=Marker('extra == "docs"')),
    ]
