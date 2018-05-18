from typing import Dict, List, Set
import json

from dotlock.exceptions import LockEnvironmentMismatch
from dotlock.resolve import Requirement, candidate_topo_sort
from dotlock.package_json import PackageJSON
from dotlock._vendored.pep425tags import get_impl_tag, get_abi_tag, get_platform, is_manylinux1_compatible


def candidate_list(requirements: List[Requirement]) -> List[Dict[str, str]]:
    return [
        {
            'name': candidate.info.name,
            'version': str(candidate.info.version),
            'package_type': candidate.info.package_type.name,
            'source': candidate.info.source,
            'url': candidate.info.url,
            'sha256': candidate.info.sha256,
        } for candidate in candidate_topo_sort(requirements)
    ]


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


def merge_requirement_lists(requirement_lists: List[List[dict]]) -> List[dict]:
    requirements = []
    requirement_names: Set[str] = set()
    for rl in requirement_lists:
        for r in rl:
            name = r['name']
            if name not in requirement_names:
                requirements.append(r)
                requirement_names.add(name)
    return requirements
