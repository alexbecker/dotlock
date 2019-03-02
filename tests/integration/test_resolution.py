import sys

import aiohttp
import pytest

from dotlock import resolve
from dotlock.dist_info.dist_info import PackageType
from dotlock.package_json import parse_requirements
from tests.unit.test_resolution import make_index_cache


@pytest.mark.asyncio
async def test_aiohttp(aiohttp_resolved_requirements):
    candidates = resolve.candidate_topo_sort(aiohttp_resolved_requirements)
    candidate_names = {candidate.info.name for candidate in candidates}

    expected_candidate_names = {
        'attrs',
        'chardet',
        'multidict',
        'async-timeout',
        'idna',
        'yarl',
        'aiohttp',
    }
    if sys.version_info < (3, 7):
        # idna-ssl is a dependency of aiohttp prior to python 3.7
        expected_candidate_names.add('idna-ssl')

    assert candidate_names == expected_candidate_names


@pytest.mark.asyncio
async def test_certbot():
    requirements = parse_requirements({'certbot': '==0.23.0'})
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

    certbot = candidates[-1].info
    assert certbot.name == 'certbot'
    assert certbot.package_type == resolve.PackageType.bdist_wheel

    candidate_names = [candidate.info.name for candidate in candidates]
    assert candidate_names == [
        'asn1crypto',
        'six',
        'pycparser',
        'cffi',
        'cryptography',
        'pyopenssl',
        'setuptools',
        'josepy',
        'pbr',
        'mock',
        'pytz',
        'pyrfc3339',
        'chardet',
        'idna',
        'urllib3',
        'certifi',
        'requests',
        'requests-toolbelt',
        'acme',
        'configargparse',
        'configobj',
        'future',
        'parsedatetime',
        'zope-interface',
        'zope-proxy',
        'zope-deferredimport',
        'zope-deprecation',
        'zope-event',
        'zope-hookable',
        'zope-component',
        'certbot',
    ]


@pytest.mark.asyncio
async def test_pyrfc3339():
    """
    Test a package that has a bdist but where PyPI requires_dist is missing.
    """
    requirements = parse_requirements({'pyrfc3339': '==1.0'})
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


@pytest.mark.asyncio
async def test_stale_cache(cache_connection):
    """
    Test a pinned requirement where the desired package is cached, but the version is missing.
    In this case we should check whether the version exists in the remote index.
    """
    requirements = parse_requirements({'attrs': '==18.2.0'})
    make_index_cache(cache_connection, {
        'attrs': {
            '18.1.0': {
                PackageType.bdist_wheel: {},
            }
        }
    })

    async with aiohttp.ClientSession() as session:
        await resolve._resolve_requirement_list(
            base_requirements=requirements,
            requirements=requirements,
            package_types=[
                resolve.PackageType.bdist_wheel,
                resolve.PackageType.sdist,
            ],
            sources=[
                'https://pypi.org/pypi',
            ],
            connection=cache_connection,
            session=session,
            update=False,
        )

    candidates = resolve.candidate_topo_sort(requirements)
    assert len(candidates) == 1
    candidate_info = candidates[0].info
    assert candidate_info.name == 'attrs'
    assert str(candidate_info.version) == '18.2.0'
