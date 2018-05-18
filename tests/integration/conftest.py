from pathlib import Path

import pytest
import virtualenv
from packaging.specifiers import SpecifierSet

from dotlock import resolve
from dotlock.tempdir import temp_working_dir


@pytest.fixture(name='aiohttp_resolved_requirements')
async def resolve_aiohttp_requirements(loop):
    requirements = [
        resolve.Requirement(
            info=resolve.RequirementInfo(
                name='aiohttp',
                specifier=SpecifierSet('==3.1.2'),
                extras=tuple(),
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
        update=False,
    )
    return requirements


@pytest.fixture(name='activate_venv')
def venv_fixture():
    with temp_working_dir():
        virtualenv.create_environment('venv')

        def activate():
            venv_script = Path('venv/bin/activate_this.py')
            with open(venv_script) as fp:
                exec(fp.read(), {'__file__': venv_script})

        yield activate
