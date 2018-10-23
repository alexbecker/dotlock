import pytest

from dotlock.tempdir import temp_working_dir


@pytest.fixture(name='tempdir')
def tempdir_fixture():
    with temp_working_dir('test'):
        yield
