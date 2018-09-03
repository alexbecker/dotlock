import asyncio
import asyncio.subprocess
import os
import os.path
import logging
from typing import List

import distlib.index

from dotlock.dist_info.vcs import clone
from dotlock.tempdir import temp_working_dir

logger = logging.getLogger(__name__)


async def download(requirement: dict):
    url = requirement['url']
    vcs_url = requirement['vcs_url']
    if vcs_url:
        logger.info('Cloning %s from %s', requirement['name'], vcs_url)
        clone_dir_name = await clone(requirement['vcs_url'])
        # Rename the cloned directory so it is unique and easy to install from.
        os.rename(clone_dir_name, requirement['name'])
    else:
        logger.info('Downloading %s from %s', requirement['name'], url)
        index = distlib.index.PackageIndex(requirement['source'])
        package_filename = requirement['url'].split('/')[-1]
        # TODO: make async
        index.download_file(
            requirement['url'],
            destfile=package_filename,
            digest=('sha256', requirement['sha256']),
        )


async def download_all(requirements: List[dict]):
    return await asyncio.gather(*[
        download(requirement) for requirement in requirements
    ])


async def install(requirements: List[dict]):
    venv_path = os.path.join(os.getcwd(), 'venv')

    with temp_working_dir('install'):
        await download_all(requirements)
        for requirement in requirements:
            args = [
                'pip', 'install',
                # Specify venv as the install target.
                '--prefix', venv_path,
                # Stop pip from checking PyPI (although this should be redundant).
                '--no-index',
                # For some reason pip tries to uninstall stuff outside ./venv without this.
                '--ignore-installed',
                # Skip installing/verifying dependencies, since we have already installed them in previous iterations.
                '--no-deps',
                # Installing sdists that use build isolation with --no-index is broken,
                # because pip will not use the installed setuptools and wheel packages to build the sdist.
                # See https://github.com/pypa/pip/issues/5402 for discussion.
                '--no-build-isolation',
            ]
            if requirement['vcs_url']:
                target_name = f'./{requirement["name"]}'
            else:
                # We can't just use requirement['name'] as the package name because
                # pip won't find the file if its (potentially non-canonical) name
                # does not match the package name.
                target_name = requirement['url'].split('/')[-1]
            args.append(target_name)
            logger.debug(' '.join(args))
            process = await asyncio.subprocess.create_subprocess_exec(*args)

            await process.wait()
