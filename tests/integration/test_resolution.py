import sys

import pytest

from dotlock import resolve


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
    requirements = [
        resolve.Requirement(
            info=resolve.RequirementInfo.from_specifier_str('certbot', '==0.23.0'),
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

    certbot = candidates[-1].info
    assert certbot.name == 'certbot'
    assert certbot.package_type == resolve.PackageType.bdist_wheel

    candidate_names = [candidate.info.name for candidate in candidates]
    assert candidate_names == [
        'idna',
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
    requirements = [
        resolve.Requirement(
            info=resolve.RequirementInfo.from_specifier_str('pyrfc3339', '==1.0'),
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
