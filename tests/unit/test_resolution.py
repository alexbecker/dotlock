import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from dotlock.caching import set_cached_candidate_infos, set_cached_requirement_infos
from dotlock.dist_info_parsing import PackageType, RequirementInfo, CandidateInfo
from dotlock.exceptions import CircularDependencyError
from dotlock.resolve import Requirement, _resolve_requirement_list, candidate_topo_sort


@pytest.mark.asyncio
async def test_resolve_no_dependencies_multiple_candidates(cache_connection):
    requirements = [
        Requirement(
            info=RequirementInfo(name='a', specifier=SpecifierSet('<2.0'), extras=tuple(), marker=None),
            parent=None,
        )
    ]

    # Create cached candidates for a.
    cached_canidate_infos = [
        CandidateInfo(name='a', version=Version('1.0'), package_type=PackageType.bdist_wheel,
                      source='https://pypi.org/pypi', url='https://a.com/1.0b', sha256='1'),
        CandidateInfo(name='a', version=Version('1.1'), package_type=PackageType.sdist,
                      source='https://pypi.org/pypi', url='https://a.com/1.1s', sha256='2'),
        # This is the candidate that should be selected!
        CandidateInfo(name='a', version=Version('1.1'), package_type=PackageType.bdist_wheel,
                      source='https://pypi.org/pypi', url='https://a.com/1.1b', sha256='3'),
        CandidateInfo(name='a', version=Version('2.0'), package_type=PackageType.bdist_wheel,
                      source='https://pypi.org/pypi', url='https://a.com/2.0b', sha256='4'),
    ]
    set_cached_candidate_infos(cache_connection, cached_canidate_infos)

    # Create cached requirements for each candidate.
    for candidate_info in cached_canidate_infos:
        set_cached_requirement_infos(cache_connection, candidate_info, [])

    await _resolve_requirement_list(
        package_types=[PackageType.bdist_wheel, PackageType.sdist],
        sources=['https://pypi.org/pypi'],
        base_requirements=requirements,
        requirements=requirements,
        connection=cache_connection,
        session=None,
        update=False,
    )
    candidates = candidate_topo_sort(requirements)
    candidate_infos = [c.info for c in candidates]

    assert candidate_infos == [cached_canidate_infos[2]]


@pytest.mark.asyncio
async def test_resolve_depth_2_dependencies(cache_connection):
    requirements = [
        Requirement(
            info=RequirementInfo(name='a', specifier=None, extras=tuple(), marker=None),
            parent=None,
        )
    ]

    # Create cached candidates for each package.
    cached_canidate_infos = [
        CandidateInfo(name='a', version=Version('1.0'), package_type=PackageType.bdist_wheel,
                      source='https://pypi.org/pypi', url='https://a.com/1.0b', sha256='a'),
        CandidateInfo(name='b', version=Version('1.0'), package_type=PackageType.bdist_wheel,
                      source='https://pypi.org/pypi', url='https://b.com/1.0b', sha256='b'),
        CandidateInfo(name='c', version=Version('1.0'), package_type=PackageType.bdist_wheel,
                      source='https://pypi.org/pypi', url='https://c.com/1.0b', sha256='c'),
    ]
    set_cached_candidate_infos(cache_connection, cached_canidate_infos)

    # Create cached requirements for each candidate.
    for i, c in enumerate(cached_canidate_infos):
        if i < 2:
            # Make a depend on b depend on c.
            requirement_name = 'abc'[i + 1]
            c_requirements = [
                RequirementInfo(name=requirement_name, specifier=None, extras=tuple(), marker=None),
            ]
        else:
            # Make c have no dependencies.
            c_requirements = []
        set_cached_requirement_infos(cache_connection, c, c_requirements)

    await _resolve_requirement_list(
        package_types=[PackageType.bdist_wheel, PackageType.sdist],
        sources=['https://pypi.org/pypi'],
        base_requirements=requirements,
        requirements=requirements,
        connection=cache_connection,
        session=None,
        update=False,
    )
    candidates = candidate_topo_sort(requirements)
    candidate_infos = [c.info for c in candidates]

    # The candidates in topo order should be the reverse of the dependency order.
    assert candidate_infos == cached_canidate_infos[::-1]


@pytest.mark.asyncio
async def test_circular_dependency(cache_connection):
    requirements = [
        Requirement(
            info=RequirementInfo(name='a', specifier=None, extras=tuple(), marker=None),
            parent=None,
        )
    ]

    # Create cached candidates for each package.
    cached_canidate_infos = [
        CandidateInfo(name='a', version=Version('1.0'), package_type=PackageType.bdist_wheel,
                      source='https://pypi.org/pypi', url='https://a.com/1.0b', sha256='a'),
        CandidateInfo(name='b', version=Version('1.0'), package_type=PackageType.bdist_wheel,
                      source='https://pypi.org/pypi', url='https://b.com/1.0b', sha256='b'),
        CandidateInfo(name='c', version=Version('1.0'), package_type=PackageType.bdist_wheel,
                      source='https://pypi.org/pypi', url='https://c.com/1.0b', sha256='c'),
    ]
    set_cached_candidate_infos(cache_connection, cached_canidate_infos)

    # Create cached requirements for each candidate.
    for i, c in enumerate(cached_canidate_infos):
        # Make a depend on b depend on c depend on a (circular).
        requirement_name = 'abc'[(i + 1) % 3]
        c_requirements = [
            RequirementInfo(name=requirement_name, specifier=None, extras=tuple(), marker=None),
        ]
        set_cached_requirement_infos(cache_connection, c, c_requirements)

    with pytest.raises(CircularDependencyError):
        await _resolve_requirement_list(
            package_types=[PackageType.bdist_wheel, PackageType.sdist],
            sources=['https://pypi.org/pypi'],
            base_requirements=requirements,
            requirements=requirements,
            connection=cache_connection,
            session=None,
            update=False,
        )
