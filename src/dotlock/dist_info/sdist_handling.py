import asyncio
import logging
import os
import sys
import distutils.core
from typing import List

from aiohttp import ClientSession
from packaging.utils import canonicalize_name

from dotlock.dist_info.dist_info import RequirementInfo, CandidateInfo, PackageType, parse_requires_dist
from dotlock.tempdir import temp_working_dir


logger = logging.getLogger(__name__)


def run_setup(*args):
    """
    Like distutils.core.run_setup('setup.py', stop_after='config')
    except sets __name__ = '__main__' which some packages require.
    See: https://bugs.python.org/issue18970

    Returns:
        A distutils.core.Distribution instance.
    """
    saved_argv = sys.argv[:]
    sys.argv[:] = ['setup.py', *args]
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

    url = candidate_info.location
    filename = url.split('/')[-1]

    with temp_working_dir():
        # Download the tarball.
        logger.debug('downloading archive %s', url)
        async with session.get(url) as response:
            with open(filename, 'wb') as fp:
                async for chunk in response.content.iter_any():
                    fp.write(chunk)

        package_dir = await extract_file(filename)
        return get_local_package_requirements(candidate_info.name, package_dir)


async def extract_file(filename: str) -> str:
    # Extract the file.
    if filename.endswith('.tar.gz'):
        ext = '.tar.gz'
        subprocess = await asyncio.create_subprocess_exec(
            'tar', '-xf', filename,
        )
    elif filename.endswith('.tar.bz2'):
        ext = '.tar.bz2'
        subprocess = await asyncio.create_subprocess_exec(
            'tar', '-xf', filename,
        )
    elif filename.endswith('.zip'):
        ext = '.zip'
        subprocess = await asyncio.create_subprocess_exec(
            'unzip', filename,
        )
    else:
        raise ValueError('Unrecognized archive format: %s', filename)

    await subprocess.wait()
    return filename[:-len(ext)]


def get_local_package_requirements(candidate_name: str, package_dir: str) -> List[RequirementInfo]:
    logger.debug('Getting local package requirements for %s from directory %s', candidate_name, package_dir)
    # CD into the extracted directory.
    # Necessary since some setup.py files expect to run from this directory.
    old_cwd = os.getcwd()
    os.chdir(package_dir)
    # Some setup.py files also expect the current directory to be in the path.
    sys.path.append(os.getcwd())

    try:
        # Parse setup.py and partially execute it.
        distribution = run_setup('sdist')
    finally:
        sys.path.pop()
        os.chdir(old_cwd)

    canonical_name = canonicalize_name(distribution.get_name())
    assert canonical_name == candidate_name, f'{canonical_name} != {candidate_name}'

    try:
        setup_requires = distribution.setup_requires
        install_requires = distribution.install_requires
    except AttributeError:
        setup_requires = []
        install_requires = distribution.get_requires()
        logger.debug('Package %s uses outdated "requires" setup kwarg.')

    if setup_requires:
        logger.warning('Package %s uses setup_requires; we cannot guarantee integrity.',
                       distribution.get_fullname())

    logger.debug('%s sdist requires: %r', candidate_name, install_requires)
    return parse_requires_dist(install_requires)
