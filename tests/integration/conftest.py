import pytest

from dotlock import resolve


def pytest_addoption(parser):
    parser.addoption(
        "--numpy", action="store_true", help="Run numpy tests (slow)."
    )


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
