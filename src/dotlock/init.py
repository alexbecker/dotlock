import logging
import os
import shutil
from pathlib import Path

import virtualenv

from dotlock.exceptions import SystemException


logger = logging.getLogger(__name__)


def init():
    if os.path.exists('venv'):
        logger.warning('virtualenv "venv" already exists, skipping creation')
    else:
        logger.info('creating virtualenv "venv"')
        try:
            virtualenv.create_environment('venv')
        except AssertionError as e:
            if 'distutils does not start with any of these prefixes' in str(e):
                # This is a shortcoming in virtualenv; it cannot handle creating a new virtualenv
                # from a virtualenv if the system python was compiled somewhere not on the PATH.
                # See https://github.com/tox-dev/tox/issues/394
                raise SystemException(
                    'System python is in a different directory than it was built for; cannot create nested virtualenv.'
                )
            raise

    if os.path.exists('package.lock'):
        logger.warning('package.lock already exists, skipping creation')
    else:
        logger.info('creating skeleton "package.lock" file')
        skeleton_path = str(Path(__file__).parent / Path('package.skeleton.json'))
        shutil.copy(skeleton_path, 'package.json')
