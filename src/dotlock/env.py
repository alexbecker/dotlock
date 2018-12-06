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
        if environment != default_environment():
            logger.warning('%s does not match environment. Dependency resolution for sdists may be inaccurate.')
        pep425tags.update(override['pep425tags'])
        if pep425tags != default_pep425tags():
            logger.warning(
                '%s does not match PEP425 tags for your environment. '
                'Dependency resolution for sdists may be inaccurate.'
            )


def dump():
    with env_file.open('w') as fp:
        json.dump({
            'environment': default_environment(),
            'pep425tags': default_pep425tags(),
        }, fp, indent=4, sort_keys=True)


# Load immediately so environment and tags are always available.
load()
