from pathlib import Path

from packaging.specifiers import SpecifierSet

from dotlock.dist_info_parsing import RequirementInfo
from dotlock.bdist_wheel_handling import get_wheel_file_requirements
from dotlock.markers import Marker


def test_get_wheel_file_requirements():
    acme_wheel_file = str(Path(__file__).parent / Path('acme-0.24.0-py2.py3-none-any.whl'))
    requirements = get_wheel_file_requirements(acme_wheel_file)

    assert requirements == [
        RequirementInfo(name='cryptography', specifier=SpecifierSet('>=0.8'), extras=tuple(), marker=None),
        RequirementInfo(name='josepy', specifier=SpecifierSet('>=1.0.0'), extras=tuple(), marker=None),
        RequirementInfo(name='mock', specifier=SpecifierSet(''), extras=tuple(), marker=None),
        RequirementInfo(name='pyopenssl', specifier=SpecifierSet('>=0.13'), extras=tuple(), marker=None),
        RequirementInfo(name='pyrfc3339', specifier=SpecifierSet(''), extras=tuple(), marker=None),
        RequirementInfo(name='pytz', specifier=SpecifierSet(''), extras=tuple(), marker=None),
        RequirementInfo(name='requests', specifier=SpecifierSet('>=2.4.1'), extras=('security',), marker=None),
        RequirementInfo(name='setuptools', specifier=SpecifierSet(''), extras=tuple(), marker=None),
        RequirementInfo(name='six', specifier=SpecifierSet('>=1.9.0'), extras=tuple(), marker=None),
        RequirementInfo(name='pytest', specifier=SpecifierSet(''), extras=tuple(), marker=Marker('extra == "dev"')),
        RequirementInfo(name='pytest-xdist', specifier=SpecifierSet(''), extras=tuple(), marker=Marker('extra == "dev"')),
        RequirementInfo(name='tox', specifier=SpecifierSet(''), extras=tuple(), marker=Marker('extra == "dev"')),
        RequirementInfo(name='sphinx', specifier=SpecifierSet('>=1.0'), extras=tuple(), marker=Marker('extra == "docs"')),
        RequirementInfo(name='sphinx-rtd-theme', specifier=SpecifierSet(''), extras=tuple(), marker=Marker('extra == "docs"')),
    ]
