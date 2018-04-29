import subprocess

import pytest

from package.install import install
from package.package_lock import candidate_list


@pytest.mark.asyncio
async def test_aiohttp(aiohttp_resolved_requirements, venv):
    candidates = candidate_list(aiohttp_resolved_requirements)
    await install(venv, candidates)

    pip_freeze = subprocess.run(['pip', 'freeze'], stdout=subprocess.PIPE)
    installed_specifiers = pip_freeze.stdout.decode('utf-8').rstrip().split('\n')
    installed_names = [specifier.split('==')[0] for specifier in installed_specifiers]

    assert sorted(c['name'] for c in candidates) == sorted(installed_names)
