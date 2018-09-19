import asyncio
import asyncio.subprocess
import hashlib
import os
import logging
import os.path
from typing import Sequence

from aiohttp import ClientSession

from dotlock.dist_info.dist_info import PackageType, CandidateInfo
from dotlock.dist_info.vcs import clone
from dotlock.exceptions import HashMismatchError
from dotlock.tempdir import temp_working_dir

logger = logging.getLogger(__name__)


async def download(session: ClientSession, candidate: CandidateInfo):
    if candidate.package_type == PackageType.vcs:
        logger.info('Cloning %s from %s', candidate.name, candidate.location)
        clone_dir_name = await clone(candidate.location)
        # Rename the cloned directory so it is unique and easy to install from.
        os.rename(clone_dir_name, candidate.name)
    elif candidate.package_type == PackageType.local:
        pass  # It's a local file.
    else:
        logger.info('Downloading %s from %s', candidate.name, candidate.location)

        async with session.get(candidate.location) as response:
            response.raise_for_status()
            # TODO: download in chunks to reduce memory usage
            contents = await response.read()

        hasher = hashlib.new(candidate.hash_alg)
        hasher.update(contents)
        digest = hasher.hexdigest()
        if digest != candidate.hash_val:
            raise HashMismatchError(candidate.name, candidate.version, digest, candidate.hash_val)

        package_filename = candidate.location.split('/')[-1]
        with open(package_filename, 'wb') as fp:
            fp.write(contents)


async def download_all(candidates: Sequence[CandidateInfo]):
    async with ClientSession() as session:
        return await asyncio.gather(*[
            download(session, candidate) for candidate in candidates
        ])


async def install(candidates: Sequence[CandidateInfo]):
    python_path = os.path.join(os.getcwd(), 'venv', 'bin', 'python')

    with temp_working_dir('install'):
        await download_all(candidates)
        for candidate in candidates:
            args = [
                python_path, '-m',
                'pip', 'install',
                # Stop pip from checking PyPI (although this should be redundant).
                '--no-index',
                # Skip installing/verifying dependencies, since we have already installed them in previous iterations.
                '--no-deps',
                # Installing sdists that use build isolation with --no-index is broken,
                # because pip will not use the installed setuptools and wheel packages to build the sdist.
                # See https://github.com/pypa/pip/issues/5402 for discussion.
                '--no-build-isolation',
            ]
            if candidate.package_type == PackageType.vcs:
                target_name = f'./{candidate.name}'
            elif candidate.package_type == PackageType.local:
                target_name = candidate.location
            else:
                # We can't just use candidate.name as the package name because
                # pip won't find the file if its (potentially non-canonical) name
                # does not match the package name.
                target_name = candidate.location.split('/')[-1]
            args.append(target_name)
            logger.debug(' '.join(args))
            process = await asyncio.subprocess.create_subprocess_exec(*args)

            await process.wait()
