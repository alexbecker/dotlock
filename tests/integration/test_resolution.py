from packaging.specifiers import SpecifierSet
import pytest

from dotlock import resolve


@pytest.mark.asyncio
async def test_aiohttp(aiohttp_resolved_requirements):
    candidates = resolve.candidate_topo_sort(aiohttp_resolved_requirements)
    candidate_names = [candidate.info.name for candidate in candidates]

    assert candidate_names == [
        'attrs',
        'chardet',
        'multidict',
        'async-timeout',
        'idna',
        'yarl',
        'aiohttp',
    ]


@pytest.mark.asyncio
async def test_certbot():
    requirements = [
        resolve.Requirement(
            info=resolve.RequirementInfo(
                name='certbot',
                specifier=SpecifierSet('==0.23.0'),
                extras=tuple(),
                marker=None,
                vcs_url=None,
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
    candidates = resolve.candidate_topo_sort(requirements)
    candidate_names = [candidate.info.name for candidate in candidates]

    assert candidate_names == [
        'setuptools',
        'zope-interface',
        'zope-event',
        'zope-component',
        'pytz',
        'pyrfc3339',
        'future',
        'parsedatetime',
        'pbr',
        'six',
        'mock',
        'idna',
        'asn1crypto',
        'pycparser',
        'cffi',
        'cryptography',
        'pyopenssl',
        'josepy',
        'configobj',
        'configargparse',
        'certifi',
        'urllib3',
        'chardet',
        'requests',
        'requests-toolbelt',
        'acme',
        'certbot',
    ]


@pytest.mark.asyncio
async def test_pyrfc3339():
    """
    Test a package that has a bdist but where PyPI requires_dist is missing.
    """
    requirements = [
        resolve.Requirement(
            info=resolve.RequirementInfo(
                name='pyrfc3339',
                specifier=SpecifierSet('==1.0'),
                extras=tuple(),
                marker=None,
                vcs_url=None,
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
    candidates = resolve.candidate_topo_sort(requirements)
    candidate_names = [candidate.info.name for candidate in candidates]

    assert candidate_names == [
        'pytz',
        'pyrfc3339',
    ]
