from typing import Dict, List

import pytest
from packaging.version import Version

from dotlock.dist_info.caching import set_cached_candidate_infos, set_cached_requirement_infos
from dotlock.dist_info.dist_info import PackageType, RequirementInfo, CandidateInfo
from dotlock.exceptions import CircularDependencyError, RequirementConflictError
from dotlock.package_json import parse_requirements
from dotlock.resolve import _resolve_requirement_list, candidate_topo_sort


def make_index_cache(cache_connection, index_state: dict) -> Dict[CandidateInfo, List[RequirementInfo]]:
    candidates_with_requirements = {}
    for package_name, package_data in index_state.items():
        for version_str, version_data in package_data.items():
            for package_type, requirement_dict in version_data.items():
                candidate = CandidateInfo(
                    name=package_name,
                    version=Version(version_str),
                    package_type=package_type,
                    source='https://pypi.org/pypi',
                    location=f'https://pypi.org/{package_name}/{version_str}/{package_type.name}',
                    hash_val=str(len(candidates_with_requirements)),  # Just needs to be unique.
                    hash_alg='fake',
                )
                candidates_with_requirements[candidate] = [
                    RequirementInfo.from_specifier_str(name, specifier_str)
                    for name, specifier_str in requirement_dict.items()
                ]

    set_cached_candidate_infos(cache_connection, list(candidates_with_requirements))
    for candidate, requirements in candidates_with_requirements.items():
        set_cached_requirement_infos(cache_connection, candidate, requirements)

    return candidates_with_requirements


@pytest.mark.asyncio
async def test_resolve_no_dependencies_multiple_candidates(cache_connection):
    requirements = parse_requirements({'a': '<2.0'})
    candidates_with_requirements = make_index_cache(cache_connection, {
        'a': {
            '1.0': {
                PackageType.bdist_wheel: {},
            },
            '1.1': {
                PackageType.bdist_wheel: {},  # This one should be selected.
                PackageType.sdist: {},
            },
            '2.0': {
                PackageType.bdist_wheel: {},
            },
        }
    })

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

    assert candidate_infos == list(candidates_with_requirements)[1:2]


@pytest.mark.asyncio
async def test_resolve_depth_2_dependencies(cache_connection):
    requirements = parse_requirements({'a': '*'})
    candidates_with_requirements = make_index_cache(cache_connection, {
        'a': {
            '1.0': {
                PackageType.bdist_wheel: {
                    'b': '*',
                }
            }
        },
        'b': {
            '1.0': {
                PackageType.bdist_wheel: {
                    'c': '*',
                }
            }
        },
        'c': {
            '1.0': {
                PackageType.bdist_wheel: {}
            }
        },
    })

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
    assert candidate_infos == list(candidates_with_requirements)[::-1]


@pytest.mark.asyncio
async def test_circular_dependency(cache_connection):
    requirements = parse_requirements({'a': '*'})
    make_index_cache(cache_connection, {
        'a': {
            '1.0': {
                PackageType.bdist_wheel: {
                    'b': '*',
                }
            }
        },
        'b': {
            '1.0': {
                PackageType.bdist_wheel: {
                    'c': '*',
                }
            }
        },
        'c': {
            '1.0': {
                PackageType.bdist_wheel: {
                    'a': '*',
                }
            }
        },
    })

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


@pytest.mark.asyncio
async def test_requirement_conflict(cache_connection):
    requirements = parse_requirements({
        # Based on a real example: https://github.com/PyCQA/astroid/issues/652
        'mypy': '*',
        'typed-ast': '<1.3.0'
    })
    make_index_cache(cache_connection, {
        'mypy': {
            '1.0': {
                PackageType.bdist_wheel: {
                    'typed-ast': '>=1.3.1',
                }
            }
        },
        'typed-ast': {
            '1.2.0': {
                PackageType.bdist_wheel: {}
            },
            '1.3.1': {
                PackageType.bdist_wheel: {}
            }
        },
    })

    with pytest.raises(RequirementConflictError) as exc_info:
        await _resolve_requirement_list(
            package_types=[PackageType.bdist_wheel, PackageType.sdist],
            sources=['https://pypi.org/pypi'],
            base_requirements=requirements,
            requirements=requirements,
            connection=cache_connection,
            session=None,
            update=False,
        )

    msg = str(exc_info.value)
    assert '>=1.3.1 via typed-ast<-mypy' in msg
    assert '<1.3.0 via typed-ast' in msg
