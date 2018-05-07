import logging
import os
import shutil
from pathlib import Path

import virtualenv


logger = logging.getLogger(__name__)


def init():
    if os.path.exists('venv'):
        logger.warning('virtualenv "venv" already exists, skipping creation')
    else:
        logger.info('creating virtualenv "venv"')
        virtualenv.create_environment('venv')

    if os.path.exists('package.lock'):
        logger.warning('package.lock already exists, skipping creation')
    else:
        logger.info('creating skeleton "package.lock" file')
        skeleton_path = str(Path(__file__).parent / Path('package.skeleton.json'))
        shutil.copy(skeleton_path, 'package.json')
