import os
from contextlib import contextmanager
from tempfile import TemporaryDirectory


@contextmanager
def temp_working_dir():
    original_wd = os.getcwd()

    with TemporaryDirectory(prefix='python-dotlock-') as dir_path:
        os.chdir(dir_path)
        yield
        os.chdir(original_wd)

