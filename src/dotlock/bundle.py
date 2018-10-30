import asyncio
import asyncio.subprocess
import os
import logging
import shutil
from pathlib import Path
from typing import Sequence

from dotlock.dist_info.dist_info import CandidateInfo
from dotlock.install import download_all

logger = logging.getLogger(__name__)


async def bundle(candidates: Sequence[CandidateInfo]):
    os.mkdir('bundle')
    original_wd = os.getcwd()
    os.chdir('bundle')
    try:
        await download_all(candidates)
    finally:
        os.chdir(original_wd)
    try:
        process = await asyncio.subprocess.create_subprocess_exec('tar', '-zcv', '-f', 'bundle.tar.gz', 'bundle')
        await process.wait()
    finally:
        shutil.rmtree('bundle')

    install_script_path = str(Path(__file__).parent / Path('install.sh'))
    shutil.copy2(install_script_path, 'install.sh')
