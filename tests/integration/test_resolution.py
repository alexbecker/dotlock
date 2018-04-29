from packaging.specifiers import SpecifierSet
import pytest

from package import resolve


@pytest.mark.asyncio
async def test_aiohttp(aiohttp_resolved_requirements):
    candidate_infos = resolve.candidate_info_topo_sort(aiohttp_resolved_requirements)
    candidate_names = [info.name for info in candidate_infos]

    assert candidate_names == [
        'idna',
        'idna-ssl',
        'multidict',
        'yarl',
        'async-timeout',
        'chardet',
        'attrs',
        'aiohttp',
    ]


@pytest.mark.asyncio
async def test_certbot():
    requirements = [
        resolve.Requirement(
            info=resolve.RequirementInfo(
                name='certbot',
                specifier=SpecifierSet('==0.23.0'),
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
        python_version='3.6',
        sources=[
            'https://pypi.org/pypi',
        ],
    )
    candidate_infos = resolve.candidate_info_topo_sort(requirements)
    candidate_names = [info.name for info in candidate_infos]

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
        'asn1crypto',
        'idna',
        'pycparser',
        'cffi',
        'cryptography',
        'pyopenssl',
        'josepy',
        'configobj',
        'configargparse',
        'certifi',
        'chardet',
        'urllib3',
        'requests',
        'acme',
        'certbot',
    ]
