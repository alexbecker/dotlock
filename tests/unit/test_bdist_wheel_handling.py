from pathlib import Path

from packaging.specifiers import SpecifierSet

from dotlock.dist_info.dist_info import RequirementInfo
from dotlock.dist_info.wheel_handling import get_wheel_file_requirements
from dotlock.markers import Marker


def test_get_wheel_file_requirements():
    acme_wheel_file = str(Path(__file__).parent / Path('acme-0.24.0-py2.py3-none-any.whl'))
    requirements = get_wheel_file_requirements(acme_wheel_file)

    assert requirements == [
        RequirementInfo.from_specifier_or_vcs('cryptography', '>=0.8'),
        RequirementInfo.from_specifier_or_vcs('josepy', '>=1.0.0'),
        RequirementInfo.from_specifier_or_vcs('mock', ''),
        RequirementInfo.from_specifier_or_vcs('pyopenssl', '>=0.13'),
        RequirementInfo.from_specifier_or_vcs('pyrfc3339', ''),
        RequirementInfo.from_specifier_or_vcs('pytz', ''),
        RequirementInfo(name='requests', specifier='>=2.4.1', extras=('security',), marker=None, vcs_url=None),
        RequirementInfo.from_specifier_or_vcs('setuptools', ''),
        RequirementInfo(name='six', specifier=SpecifierSet('>=1.9.0'), extras=tuple(), marker=None, vcs_url=None),
        RequirementInfo(name='pytest', specifier=SpecifierSet(''), extras=tuple(), marker=Marker('extra == "dev"'),
                        vcs_url=None),
        RequirementInfo(name='pytest-xdist', specifier=SpecifierSet(''), extras=tuple(),
                        marker=Marker('extra == "dev"'), vcs_url=None),
        RequirementInfo(name='tox', specifier=SpecifierSet(''), extras=tuple(), marker=Marker('extra == "dev"'),
                        vcs_url=None),
        RequirementInfo(name='sphinx', specifier=SpecifierSet('>=1.0'), extras=tuple(),
                        marker=Marker('extra == "docs"'), vcs_url=None),
        RequirementInfo(name='sphinx-rtd-theme', specifier=SpecifierSet(''), extras=tuple(),
                        marker=Marker('extra == "docs"'), vcs_url=None),
    ]
