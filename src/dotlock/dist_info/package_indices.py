"""Functions for making API requests to PyPI."""
from typing import List, Optional
import logging

from aiohttp import ClientSession

from dotlock.dist_info import json_api, simple_api
from dotlock.dist_info.dist_info import CandidateInfo, RequirementInfo, PackageType, parse_requires_dist
from dotlock.exceptions import NotFound


logger = logging.getLogger(__name__)


async def get_candidate_infos(
        package_types: List[PackageType],
        sources: List[str],
        session: ClientSession,
        name: str,
) -> List[CandidateInfo]:
    for source in sources:
        if source.endswith('simple'):
            result = await simple_api.get_candidate_infos(package_types, source, session, name)
        else:
            result = await json_api.get_candidate_infos(package_types, source, session, name)

        if result is not None:
            return result

    raise NotFound(name, version=None)


async def get_requirment_infos(
        session: ClientSession,
        candidate: CandidateInfo,
) -> Optional[List[RequirementInfo]]:
    if candidate.source.endswith('simple'):
        return None
    metadata = await json_api.get_json_metadata(candidate.source, session, candidate.name, candidate.version)
    if metadata is None:
        return None
    requires_dist = metadata['info']['requires_dist']
    if requires_dist is not None:
        return parse_requires_dist(requires_dist)
    return None

