import sqlite3
import os
import os.path

import pytest
import aiohttp

from dotlock.dist_info.caching import setup_script


@pytest.fixture(name='cache_connection')
def mock_cache_connection():
    db_path = os.path.abspath('tmp.sqlite3')
    connection = sqlite3.connect(db_path)
    connection.executescript(setup_script)
    yield connection
    os.remove(db_path)


@pytest.fixture(name='session')
async def mock_session():
    async with aiohttp.ClientSession() as session:
        yield session
