import asyncio
import asyncio.subprocess
import os
import os.path
import logging
import distlib.index
from tempfile import TemporaryDirectory
from typing import List


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


async def install(venv_path: str, requirements: List[dict]):
    with TemporaryDirectory(prefix='python-package-') as dir:
        await download_all(dir, requirements)
        for requirement in requirements:
            # We can't just use requirement['name'] as the package name because
            # pip won't find the file if its (potentially non-canonical) name
            # does not match the package name.
            filename = requirement['url'].split('/')[-1]
            package_name = filename.split('-')[0]

            if requirement['package_type'] == 'sdist':
                process = await asyncio.subprocess.create_subprocess_exec(
                    'pip', 'install', '--no-index',
                    '--prefix', venv_path,
                    '--find-links', dir,
                    package_name,
                )
            else:
                process = await asyncio.subprocess.create_subprocess_exec(
                    'pip', 'install', '--no-index',
                    '--prefix', venv_path,
                    '--find-links', dir,
                    os.path.join(dir, filename),
                )

            await process.wait()
