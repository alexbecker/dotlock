from typing import Dict, Iterable, Tuple
import json

from dotlock.dist_info.dist_info import CandidateInfo
from dotlock.exceptions import LockEnvironmentMismatch
from dotlock.resolve import Requirement, candidate_topo_sort
from dotlock.package_json import PackageJSON
from dotlock._vendored.pep425tags import get_impl_tag, get_abi_tag, get_platform, is_manylinux1_compatible


def candidate_list(requirements: Tuple[Requirement, ...]) -> Tuple[Dict[str, str], ...]:
    return tuple(
        candidate.info.to_json()
        for candidate in candidate_topo_sort(requirements)
    )


def package_lock_data(package_json: PackageJSON) -> dict:
    return {
        'python': get_impl_tag(),
        'abi': get_abi_tag(),
        'platform': get_platform(),
        'manylinux1': is_manylinux1_compatible(),
        'default': candidate_list(package_json.default),
        'extras': {
            key: candidate_list(reqs)
            for key, reqs in package_json.extras.items()
        },
    }


def write_package_lock(package_json: PackageJSON) -> None:
    data = package_lock_data(package_json)
    with open('package.lock.json', 'w') as fp:
        json.dump(data, fp, indent=4, sort_keys=True)


def load_package_lock() -> dict:
    with open('package.lock.json') as fp:
        return json.load(fp)


def check_lock_environment(lock_data: dict) -> None:
    if lock_data['python'] != get_impl_tag():
        raise LockEnvironmentMismatch('python', lock_data['python'], get_impl_tag())
    if lock_data['abi'] != get_abi_tag():
        raise LockEnvironmentMismatch('abi', lock_data['abi'], get_abi_tag())
    if lock_data['platform'] != get_platform():
        raise LockEnvironmentMismatch('platform', lock_data['platform'], get_platform())
    if lock_data['manylinux1'] != is_manylinux1_compatible():
        raise LockEnvironmentMismatch('manylinux1', lock_data['manylinux1'], is_manylinux1_compatible())


def get_locked_candidates(lock_data: dict, extras: Iterable[str]) -> Tuple[CandidateInfo, ...]:
    candidate_lists = [lock_data['default']] + [lock_data['extras'][extra] for extra in extras]
    # Use a dictionary to remove duplicates.
    by_name = {
        c['name']: CandidateInfo.from_json(c)
        for cl in candidate_lists
        for c in cl
    }
    return tuple(by_name.values())
