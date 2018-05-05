import pytest
import virtualenv
from packaging.specifiers import SpecifierSet

from package import resolve
from package.tempdir import temp_working_dir


@pytest.fixture(name='aiohttp_resolved_requirements')
async def resolve_aiohttp_requirements():
    requirements = [
        resolve.Requirement(
            info=resolve.RequirementInfo(
                name='aiohttp',
                specifier=SpecifierSet('==3.1.2'),
                extra=None,
                marker=None,
            ),
            parent=None,
        ),
    ]
    await resolve.resolve_requirements_list(
        requirements=requirements,
        package_types=[
            resolve.PackageType.bdist_wheel,
            resolve.PackageType.sdist,
        ],
        sources=[
            'https://pypi.org/pypi',
        ],
    )
    return requirements


@pytest.fixture(name='venv')
def venv_fixture():
    with temp_working_dir():
        virtualenv.create_environment('venv')
        yield
