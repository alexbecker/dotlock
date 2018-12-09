import sqlite3
import os
import os.path

import pytest

from dotlock.dist_info.caching import setup_script
from dotlock.tempdir import temp_working_dir


@pytest.fixture(name='tempdir')
def tempdir_fixture():
    with temp_working_dir('test'):
        yield


@pytest.fixture(name='cache_connection')
def mock_cache_connection():
    db_path = os.path.abspath('tmp.sqlite3')
    connection = sqlite3.connect(db_path)
    connection.executescript(setup_script)
    yield connection
    os.remove(db_path)
