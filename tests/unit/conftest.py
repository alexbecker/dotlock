import sqlite3
import os

import pytest
import aiohttp

from dotlock.caching import setup_script


@pytest.fixture(name='cache_connection')
def mock_cache_connection():
    connection = sqlite3.connect('tmp.sqlite3')
    connection.executescript(setup_script)
    yield connection
    os.remove('tmp.sqlite3')


@pytest.fixture(name='session')
async def mock_session():
    async with aiohttp.ClientSession() as session:
        yield session
