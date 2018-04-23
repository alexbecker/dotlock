from typing import Dict, List, Iterable
import json

from package.resolve import Requirement, CandidateInfo
from package.package_json import PackageJSON


def _iter_live_candidate_info(requirements: Iterable[Requirement]) -> Iterable[CandidateInfo]:
    for requirement in requirements:
        for candidate in requirement.candidates.values():
            if candidate.live:
                yield candidate.info
                yield from _iter_live_candidate_info(candidate.requirements.values())


def flatten_live_candidates(requirements: List[Requirement]) -> Dict[str, Dict[str, str]]:
    return {
        candidate_info.name: {
            'version': str(candidate_info.version),
            'package_type': candidate_info.package_type.name,
            'source': candidate_info.source,
            'sha256': candidate_info.sha256,
        }
        for candidate_info in _iter_live_candidate_info(requirements)
    }


def write_package_lock(package_json: PackageJSON):
    with open('package-lock.json', 'w') as fp:
        json.dump({
            'python_version': package_json.python_version,
            'default': flatten_live_candidates(package_json.default),
        }, fp, indent=4, sort_keys=True)
