"""Functions for making API requests to PyPI."""
from typing import List, Optional
import logging

from aiohttp import ClientSession
from packaging.version import Version

from dotlock.exceptions import NotFound


logger = logging.getLogger(__name__)


async def _get_metadata(sources: List[str], session: ClientSession, name: str, version: Optional[Version]) -> (str, dict):
    for source in sources:
        if version is None:
            url = f'{source}/{name}/json'
        else:
            url = f'{source}/{name}/{version}/json'

        logger.debug('Making API request: %s', url)
        async with session.get(url) as response:
            if response.status == 404:
                continue
            response.raise_for_status()
            content = await response.json()
            return source, content

    raise NotFound(name, version)


async def get_source_and_base_metadata(sources: List[str], session: ClientSession, name: str) -> (str, dict):
    return await _get_metadata(sources, session, name, version=None)


async def get_version_metadata(source: str, session: ClientSession, name: str, version: Version) -> dict:
    _, metadata = await _get_metadata([source], session, name, version)
    return metadata
