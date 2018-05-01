from tempfile import TemporaryDirectory
from typing import List
import logging
import os

from aiohttp import ClientSession
from distlib.wheel import Wheel
from packaging.markers import Marker
from packaging.requirements import Requirement as PackagingRequirement
from packaging.utils import canonicalize_name

from package.dist_info_parsing import RequirementInfo, PackageType


logger = logging.getLogger(__name__)


async def get_bdist_wheel_requirements(session: ClientSession, candidate: 'Candidate') -> List[RequirementInfo]:
    assert candidate.info.package_type == PackageType.bdist_wheel
    logger.debug('%s has null requirements in index, so we are forced to download it', candidate.info.name)

    url = candidate.info.url
    filename = url.split('/')[-1]

    requirements = []
    with TemporaryDirectory(prefix='python-package-') as tmpdir:
        cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # Download the wheel.
            logger.debug('downloading wheel %s', candidate.info.url)
            async with session.get(candidate.info.url) as response:
                with open(filename, 'wb') as fp:
                    async for chunk in response.content.iter_any():
                        fp.write(chunk)

            wheel = Wheel(filename)
            try:
                dependencies_dict = wheel.metadata.dependencies
            except NotImplementedError:
                dependencies_dict = wheel.metadata.dictionary
            logger.debug('distlib found dependencies for %s: %r', candidate.info.name, dependencies_dict)
            dependencies_list = dependencies_dict.get('setup_requires', []) + dependencies_dict.get('run_requires', [])
            for subdict in dependencies_list:
                extra = subdict.get('extra')
                if extra and extra not in candidate.extras:
                    logging.debug('Skipping dependencies for extra %s', extra)
                    continue

                environment = subdict.get('environment')
                marker = Marker(environment) if environment else None
                for r in subdict['requires']:
                    r = PackagingRequirement(r)
                    requirements.append(RequirementInfo(
                        name=canonicalize_name(r.name),
                        specifier=r.specifier,
                        extra=extra,
                        marker=marker,
                    ))
        finally:
            os.chdir(cwd)

    return requirements
