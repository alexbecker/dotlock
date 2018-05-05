from typing import List
import logging
import os
import zipfile

from aiohttp import ClientSession
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from pkg_resources import parse_requirements

from dotlock.dist_info_parsing import RequirementInfo, CandidateInfo, PackageType
from dotlock.markers import Marker
from dotlock.tempdir import temp_working_dir


logger = logging.getLogger(__name__)


async def get_bdist_wheel_requirements(session: ClientSession, candidate_info: CandidateInfo) -> List[RequirementInfo]:
    assert candidate_info.package_type == PackageType.bdist_wheel
    logger.debug('%s has null requirements in index, so we are forced to download it', candidate_info.name)

    url = candidate_info.url
    filename = url.split('/')[-1]

    with temp_working_dir():
        # Download the wheel.
        logger.debug('downloading wheel %s', candidate_info.url)
        async with session.get(candidate_info.url) as response:
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
            for line in fp:
                line = line.decode('utf-8')
                req_prefix = 'Requires-Dist:'
                if line.startswith(req_prefix):
                    line = line[len(req_prefix):].strip()
                    requirement_lines.append(line)

    rv = []
    parsed_requirements = parse_requirements(requirement_lines)
    for r in parsed_requirements:
        extra = r.extras[0] if r.extras else None
        # pkg_resources vendors packaging so we have to change the type so comparisons work
        specifier = SpecifierSet(str(r.specifier))
        marker = Marker(str(r.marker)) if r.marker else None
        rv.append(RequirementInfo(
            name=canonicalize_name(r.name),
            specifier=specifier,
            extra=extra,
            marker=marker,
        ))

    return rv
