import asyncio
import asyncio.subprocess
import os
import os.path
import logging
from tempfile import TemporaryDirectory
from typing import List

import distlib.index


logger = logging.getLogger(__name__)


async def download(dir: str, requirement: dict):
    logger.info('Downloading %s from %s', requirement['name'], requirement['url'])
    index = distlib.index.PackageIndex(requirement['source'])
    package_filename = requirement['url'].split('/')[-1]
    destfile = os.path.join(dir, package_filename)
    index.download_file(
        requirement['url'],
        destfile=destfile,
        digest=('sha256', requirement['sha256']),
    )


async def download_all(dir: str, requirements: List[dict]):
    return await asyncio.gather(*[
        download(dir, requirement) for requirement in requirements
    ])


async def install(requirements: List[dict]):
    venv_path = os.path.join(os.getcwd(), 'venv')

    with TemporaryDirectory(prefix='python-package-') as dir:
        await download_all(dir, requirements)
        for requirement in requirements:
            # We can't just use requirement['name'] as the package name because
            # pip won't find the file if its (potentially non-canonical) name
            # does not match the package name.
            filename = requirement['url'].split('/')[-1]
            process = await asyncio.subprocess.create_subprocess_exec(
                'pip', 'install', '--no-index',
                '--target', os.path.join(venv_path, 'lib/python3.6/site-packages/'),
                '--find-links', dir,
                os.path.join(dir, filename),
            )

            await process.wait()
