from typing import Dict, List
import json

from package.resolve import Requirement, candidate_info_topo_sort
from package.package_json import PackageJSON


def candidate_list(requirements: List[Requirement]) -> List[Dict[str, str]]:
    return [
        {
            'name': candidate_info.name,
            'version': str(candidate_info.version),
            'package_type': candidate_info.package_type.name,
            'source': candidate_info.source,
            'url': candidate_info.url,
            'sha256': candidate_info.sha256,
        } for candidate_info in candidate_info_topo_sort(requirements)
    ]


def write_package_lock(package_json: PackageJSON):
    with open('package-lock.json', 'w') as fp:
        json.dump({
            'python_version': package_json.python_version,
            'default': candidate_list(package_json.default),
        }, fp, indent=4, sort_keys=True)


def load_package_lock(file_path: str) -> dict:
    with open(file_path) as fp:
        return json.load(fp)