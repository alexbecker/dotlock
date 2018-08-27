import logging
import os
from contextlib import contextmanager
from tempfile import TemporaryDirectory

logger = logging.getLogger(__name__)


@contextmanager
def temp_working_dir(extra_prefix=''):
    prefix = 'python-dotlock-'
    if extra_prefix:
        prefix += f'{extra_prefix}-'

    original_wd = os.getcwd()
    with TemporaryDirectory(prefix=prefix) as dir_path:
        logger.debug(f'entering {dir_path}')
        os.chdir(dir_path)
        yield
        logger.debug(f'exiting {dir_path}')
        os.chdir(original_wd)
