import subprocess

import pytest

from dotlock.install import install
from dotlock.resolve import candidate_topo_sort


@pytest.mark.asyncio
async def test_aiohttp(aiohttp_resolved_requirements, activate_venv):
    candidate_infos = [candidate.info for candidate in candidate_topo_sort(aiohttp_resolved_requirements)]
    await install(candidate_infos)

    # Activate the target venv to get the list of installed packages via pip freeze.
    activate_venv()
    pip_freeze = subprocess.run(['pip', 'freeze'], stdout=subprocess.PIPE)
    installed_specifiers = pip_freeze.stdout.decode('utf-8').rstrip().split('\n')
    installed_names = [specifier.split('==')[0] for specifier in installed_specifiers]

    assert sorted(c.name for c in candidate_infos) == sorted(installed_names)
