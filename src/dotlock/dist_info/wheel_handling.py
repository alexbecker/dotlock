from typing import List
import logging
import os
import zipfile

from aiohttp import ClientSession
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from pkg_resources import parse_requirements

from dotlock.dist_info.dist_info import RequirementInfo, CandidateInfo, PackageType, SpecifierType
from dotlock.markers import Marker
from dotlock.tempdir import temp_working_dir


logger = logging.getLogger(__name__)


async def get_bdist_wheel_requirements(session: ClientSession, candidate_info: CandidateInfo) -> List[RequirementInfo]:
    assert candidate_info.package_type == PackageType.bdist_wheel
    logger.debug('%s has null requirements in index, so we are forced to download it', candidate_info.name)

    url = candidate_info.location
    filename = url.split('/')[-1]

    with temp_working_dir():
        # Download the wheel.
        logger.debug('downloading wheel %s', url)
        async with session.get(url) as response:
            with open(filename, 'wb') as fp:
                async for chunk in response.content.iter_any():
                    fp.write(chunk)

        return get_wheel_file_requirements(filename)


def get_wheel_file_requirements(filename: str) -> List[RequirementInfo]:
    relative_name = os.path.split(filename)[-1]
    dist_info_dirname = '-'.join(relative_name.split('-')[:2]) + '.dist-info'
    metadata_name = os.path.join(dist_info_dirname, 'METADATA')

    requirement_lines = []
    with zipfile.ZipFile(filename) as wheel_zip:
        with wheel_zip.open(metadata_name) as fp:
            for line_bytes in fp:
                line = line_bytes.decode('utf-8')
                req_prefix = 'Requires-Dist:'
                if line.startswith(req_prefix):
                    line = line[len(req_prefix):].strip()
                    requirement_lines.append(line)

    rv = []
    parsed_requirements = parse_requirements(requirement_lines)
    for r in parsed_requirements:
        # pkg_resources vendors packaging so we have to change the type so comparisons work
        specifier = SpecifierSet(str(r.specifier))  # type: ignore
        marker = Marker(str(r.marker)) if r.marker else None  # type: ignore
        rv.append(RequirementInfo(
            name=canonicalize_name(r.name),  # type: ignore
            # TODO: can wheels depend on VCS urls?
            specifier_type=SpecifierType.version,
            specifier=specifier,
            extras=tuple(r.extras),
            marker=marker,
        ))

    return rv
