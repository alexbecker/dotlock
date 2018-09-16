from typing import Dict, List, Optional
import logging

from aiohttp import ClientSession
from packaging.version import Version, InvalidVersion

from dotlock.exceptions import UnsupportedHashFunctionError
from dotlock.dist_info.dist_info import CandidateInfo, PackageType, hash_algorithms
from dotlock.dist_info.wheel_filename_parsing import is_supported


logger = logging.getLogger(__name__)


async def get_json_metadata(
       source: str, session: ClientSession, name: str, version: Optional[Version]
) -> Optional[Dict[str, dict]]:
    if version is None:
        url = f'{source}/{name}/json'
    else:
        url = f'{source}/{name}/{version}/json'

    logger.debug('Making API request: %s', url)
    async with session.get(url) as response:
        if response.status == 404:
            return None
        response.raise_for_status()
        return await response.json()


async def get_candidate_infos(
        package_types: List[PackageType],
        source: str,
        session: ClientSession,
        name: str,
) -> Optional[List[CandidateInfo]]:
    base_metadata = await get_json_metadata(source, session, name, version=None)
    if base_metadata is None:
        return None

    candidate_infos = []
    for version_str, distributions in base_metadata['releases'].items():
        try:
            version = Version(version_str)
        except InvalidVersion:
            logger.info('Invalid version for %r: %s', name, version_str)
            continue  # Skip candidates without a valid version.

        for distribution in distributions:
            package_type = PackageType[distribution['packagetype']]

            if package_type.name.startswith('bdist'):
                filename = distribution['filename']
                if not is_supported(filename):
                    logger.debug('Skipping unsupported bdist %s', filename)
                    continue

            if package_type not in package_types:
                logger.debug('Skipping package type %s for %s', package_type.name, name)
                continue

            for hash_alg in hash_algorithms:
                hash_val = distribution['digests'].get(hash_alg)
                if hash_val:
                    break
            else:
                raise UnsupportedHashFunctionError(hash_alg)

            candidate_infos.append(CandidateInfo(
                name=name,
                version=version,
                package_type=package_type,
                source=source,
                location=distribution['url'],
                hash_alg=hash_alg,
                hash_val=hash_val,
            ))

    return candidate_infos
