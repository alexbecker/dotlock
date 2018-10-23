from typing import Dict, Iterable, Tuple, Container, Optional
import logging
import json

from dotlock.dist_info.dist_info import CandidateInfo
from dotlock.env import environment, pep425tags, default_environment, default_pep425tags
from dotlock.exceptions import LockEnvironmentMismatch
from dotlock.resolve import Requirement, candidate_topo_sort
from dotlock.package_json import PackageJSON


logger = logging.getLogger(__name__)


def candidate_list(requirements: Tuple[Requirement, ...]) -> Tuple[Dict[str, str], ...]:
    return tuple(
        candidate.info.to_json()
        for candidate in candidate_topo_sort(requirements)
    )


def package_lock_data(package_json: PackageJSON) -> dict:
    return {
        'environment': environment,
        'pep425tags': pep425tags,
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
    for key, value in default_pep425tags().items():
        lock_value = lock_data['pep425tags'][key]
        if value != lock_value:
            raise LockEnvironmentMismatch(key, lock_value, value)
    if default_environment() != lock_data['environment']:
        logger.warning(
            'The current environment does not match the one used to generate package.lock.json. '
            'Marker evaluation may be inaccurate.'
        )


def get_locked_candidates(
        lock_data: dict, extras: Iterable[str], name_filter: Optional[Container[str]],
) -> Tuple[CandidateInfo, ...]:
    candidate_lists = [lock_data['default']] + [lock_data['extras'][extra] for extra in extras]
    # Use a dictionary to remove duplicates.
    by_name = {
        c['name']: CandidateInfo.from_json(c)
        for cl in candidate_lists
        for c in cl
        if name_filter is None or c['name'] in name_filter
    }
    return tuple(by_name.values())
