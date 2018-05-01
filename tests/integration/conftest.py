import os
import shutil
import sys

import pytest
import virtualenv
from packaging.specifiers import SpecifierSet

from package import resolve


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
    venv_dir = 'test_venv'
    virtualenv.create_environment(venv_dir)
    venv_script = os.path.join(venv_dir, 'bin', 'activate_this.py')

    old_path = sys.path

    try:
        with open(venv_script) as fp:
            exec(fp.read(), {'__file__': venv_script})

        yield venv_dir
    finally:
        sys.path = old_path
        shutil.rmtree(venv_dir)
