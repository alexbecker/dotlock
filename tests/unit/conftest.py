import pytest
import aiohttp


@pytest.fixture(name='session')
async def mock_session():
    async with aiohttp.ClientSession() as session:
        yield session
