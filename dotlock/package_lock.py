from typing import Dict, List
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


def write_package_lock(package_json: PackageJSON):
    with open('package.lock.json', 'w') as fp:
        json.dump({
            'python_version': package_json.python_version,
            'default': candidate_list(package_json.default),
        }, fp, indent=4, sort_keys=True)


def load_package_lock(file_path: str) -> dict:
    with open(file_path) as fp:
        return json.load(fp)
