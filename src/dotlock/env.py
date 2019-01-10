import json
import logging
from pathlib import Path
from typing import Dict

from packaging.markers import default_environment

from dotlock._vendored.pep425tags import (
    get_abbr_impl, get_abi_tag, get_platform, is_manylinux1_compatible, get_impl_version_info,
)


logger = logging.getLogger(__name__)

env_file = Path('env.json')
environment: Dict[str, str] = {}
pep425tags: Dict[str, str] = {}


def default_pep425tags():
    return {
        'impl': get_abbr_impl(),
        'abi': get_abi_tag(),
        'platform': get_platform(),
        'manylinux1': is_manylinux1_compatible(),
        'version': '{}.{}'.format(*get_impl_version_info()),
    }


def load():
    environment.update(default_environment())
    pep425tags.update(default_pep425tags())
    if env_file.exists():
        with env_file.open() as fp:
            override = json.load(fp)
        environment.update(override['environment'])
        platform_environment = default_environment()
        diff_keys = [key for key, value in environment.items() if value != platform_environment[key]]
        if diff_keys:
            logger.warning(
                'Platform env values %s do not match env file. Dependency resolution for sdists may be inaccurate.',
                ', '.join(diff_keys),
            )
        pep425tags.update(override['pep425tags'])
        platform_pep425tags = default_pep425tags()
        diff_keys = [key for key, value in pep425tags.items() if value != platform_pep425tags[key]]
        if diff_keys:
            logger.warning(
                'Platform PEP425 tags %s do not match env file. Dependency resolution for sdists may be inaccurate.',
                ', '.join(diff_keys),
            )


def dump():
    with env_file.open('w') as fp:
        json.dump({
            'environment': default_environment(),
            'pep425tags': default_pep425tags(),
        }, fp, indent=4, sort_keys=True)


# Load immediately so environment and tags are always available.
load()
