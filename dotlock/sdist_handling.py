import asyncio
import logging
import os
import sys
import distutils.core
from typing import List
from tempfile import TemporaryDirectory

from aiohttp import ClientSession
from packaging.utils import canonicalize_name

from dotlock.dist_info_parsing import RequirementInfo, CandidateInfo, PackageType, parse_requires_dist
from dotlock.tempdir import temp_working_dir


logger = logging.getLogger(__name__)


def run_setup():
    """
    Like distutils.core.run_setup('setup.py', stop_after='config')
    except sets __name__ = '__main__' which some packages require.

    Returns:
        A distutils.core.Distribution instance.
    """
    saved_argv = sys.argv[:]
    sys.argv[0] = 'setup.py'
    distutils.core._setup_stop_after = 'config'

    try:
        with open('setup.py') as fp:
            exec(fp.read(), {
                '__file__': 'setup.py',
                '__name__': '__main__',
            })
    finally:
        sys.argv = saved_argv
        distutils.core._setup_stop_after = None

    return distutils.core._setup_distribution


async def get_sdist_requirements(session: ClientSession, candidate_info: CandidateInfo) -> List[RequirementInfo]:
    """
    Getting the requirements for an sdist package is waaaaay more work than it should be.

    Args:
        session: an open aiohttp.ClientSession for making repeated queries to PyPI
        candidate_info: specifies the candidate that we want requirements for

    Returns:
        A list of RequirementInfo for the candidate.
    """
    assert candidate_info.package_type == PackageType.sdist
    logger.debug('%s is an sdist, doing the sdist dance to get requirements', candidate_info.name)

    url = candidate_info.url
    filename = url.split('/')[-1]

    with temp_working_dir():
        # Download the tarball.
        logger.debug('downloading archive %s', candidate_info.url)
        async with session.get(candidate_info.url) as response:
            with open(filename, 'wb') as fp:
                async for chunk in response.content.iter_any():
                    fp.write(chunk)

        return await get_sdist_file_requirements(candidate_info.name, filename)


async def get_sdist_file_requirements(candidate_name: str, filename: str) -> List[RequirementInfo]:
    # Extract the file.
    if filename.endswith('.tar.gz'):
        tar_process = await asyncio.create_subprocess_exec(
            'tar', '-xf', filename,
        )
        await tar_process.wait()
        extracted_dir = filename[:-len('.tar.gz')]
    elif filename.endswith('.zip'):
        zip_process = await asyncio.create_subprocess_exec(
            'unzip', filename,
        )
        await zip_process.wait()
        extracted_dir = filename[:-len('.zip')]
    else:
        raise ValueError('Unrecognized archive format: %s', filename)

    # CD into the extracted directory.
    # Necessary since some setup.py files expect to run from this directory.
    os.chdir(extracted_dir)
    # Some setup.py files also expect the current directory to be in the path.
    sys.path.append(os.getcwd())

    try:
        # Parse setup.py and partially execute it.
        distribution = run_setup()
    finally:
        sys.path.pop()

    canonical_name = canonicalize_name(distribution.get_name())
    assert canonical_name == candidate_name, canonical_name

    if distribution.setup_requires:
        logger.warning('Package %s uses setup_requires; we cannot guarantee integrity.',
                       distribution.get_fullname())

    requires = distribution.install_requires
    logger.debug('%s sdist requires: %r', candidate_name, requires)
    return parse_requires_dist(requires)
