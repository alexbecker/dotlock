from typing import Dict, List, Set, Tuple
import json

from dotlock.exceptions import LockEnvironmentMismatch
from dotlock.resolve import Requirement, candidate_topo_sort
from dotlock.package_json import PackageJSON
from dotlock._vendored.pep425tags import get_impl_tag, get_abi_tag, get_platform, is_manylinux1_compatible


def candidate_list(requirements: Tuple[Requirement, ...]) -> Tuple[Dict[str, str], ...]:
    return tuple(
        {
            'name': candidate.info.name,
            'version': str(candidate.info.version),
            'package_type': candidate.info.package_type.name,
            'source': candidate.info.source,
            'url': candidate.info.url,
            'vcs_url': candidate.info.vcs_url,
            'hash_alg': candidate.info.hash_alg,
            'hash_val': candidate.info.hash_val,
        } for candidate in candidate_topo_sort(requirements)
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


def load_package_lock(file_path: str) -> dict:
    with open(file_path) as fp:
        lock_data = json.load(fp)

    if lock_data['python'] != get_impl_tag():
        raise LockEnvironmentMismatch('python', lock_data['python'], get_impl_tag())
    if lock_data['abi'] != get_abi_tag():
        raise LockEnvironmentMismatch('abi', lock_data['abi'], get_abi_tag())
    if lock_data['platform'] != get_platform():
        raise LockEnvironmentMismatch('platform', lock_data['platform'], get_platform())
    if lock_data['manylinux1'] != is_manylinux1_compatible():
        raise LockEnvironmentMismatch('manylinux1', lock_data['manylinux1'], is_manylinux1_compatible())

    return lock_data


def merge_candidate_lists(candidate_lists: List[List[dict]]) -> List[dict]:
    candidates = []
    candidate_names: Set[str] = set()
    for rl in candidate_lists:
        for r in rl:
            name = r['name']
            if name not in candidate_names:
                candidates.append(r)
                candidate_names.add(name)
    return candidates
