from pathlib import Path

import pytest
import virtualenv

from dotlock import resolve
from dotlock.tempdir import temp_working_dir


@pytest.fixture(name='aiohttp_resolved_requirements')
async def resolve_aiohttp_requirements(event_loop):
    requirements = [
        resolve.Requirement(
            info=resolve.RequirementInfo.from_specifier_str('aiohttp', '==3.1.2'),
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
