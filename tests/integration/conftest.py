from pathlib import Path
import logging

import pytest
import virtualenv
from packaging.specifiers import SpecifierSet

from dotlock import resolve
from dotlock.tempdir import temp_working_dir


logging.getLogger('dotlock').setLevel(logging.DEBUG)


@pytest.fixture(name='aiohttp_resolved_requirements')
async def resolve_aiohttp_requirements(event_loop):
    requirements = [
        resolve.Requirement(
            info=resolve.RequirementInfo(
                name='aiohttp',
                vcs_url=None,
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
            venv_script = Path('venv/bin/activate_this.py').absolute()
            with venv_script.open() as fp:
                exec(fp.read(), {'__file__': venv_script})

        yield activate
