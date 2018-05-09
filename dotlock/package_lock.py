from typing import Dict, List
from platform import python_version
import json

from dotlock.resolve import Requirement, candidate_topo_sort
from dotlock.package_json import PackageJSON


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


def package_lock_data(package_json: PackageJSON):
    return {
        'python_version': python_version(),
        'default': candidate_list(package_json.default),
        'extras': {
            key: candidate_list(reqs)
            for key, reqs in package_json.extras.items()
        },
    }


def write_package_lock(package_json: PackageJSON):
    data = package_lock_data(package_json)
    with open('package.lock.json', 'w') as fp:
        json.dump(data, fp, indent=4, sort_keys=True)


def load_package_lock(file_path: str) -> dict:
    with open(file_path) as fp:
        return json.load(fp)


def merge_requirement_lists(requirement_lists: List[List[dict]]):
    requirements = []
    requirement_names = set()
    for rl in requirement_lists:
        for r in rl:
            name = r['name']
            if name not in requirement_names:
                requirements.append(r)
                requirement_names.add(name)
    return requirements
