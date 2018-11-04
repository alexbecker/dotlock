import pytest

from dotlock.tempdir import temp_working_dir


def pytest_addoption(parser):
    parser.addoption(
        "--numpy", action="store_true", help="Run numpy tests (slow)."
    )


@pytest.fixture(name='tempdir')
def tempdir_fixture():
    with temp_working_dir('test'):
        yield
