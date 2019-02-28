from pathlib import Path
import shutil
import subprocess

import pytest
import virtualenv

from dotlock.__main__ import _main
from dotlock.install import install
from dotlock.package_lock import load_package_lock, check_lock_environment, LockEnvironmentMismatch
from dotlock.resolve import candidate_topo_sort


@pytest.fixture(name='venv')
def setup_venv():
    virtualenv.create_environment('venv')


@pytest.mark.asyncio
async def test_aiohttp(aiohttp_resolved_requirements, tempdir, venv):
    candidate_infos = [candidate.info for candidate in candidate_topo_sort(aiohttp_resolved_requirements)]
    await install(candidate_infos, no_venv=False)

    # Get the list of installed packages via pip freeze.
    pip_freeze = subprocess.run(['dotlock', 'run', 'pip', 'freeze'], stdout=subprocess.PIPE)
    installed_specifiers = pip_freeze.stdout.decode('utf-8').rstrip().split('\n')
    installed_names = [specifier.split('==')[0] for specifier in installed_specifiers]

    assert sorted(c.name for c in candidate_infos) == sorted(installed_names)


def test_install_from_lock(tempdir, venv):
    testfile_path = str(Path(__file__).parent / Path('package.lock.json'))
    shutil.copy(testfile_path, 'package.lock.json')

    package_lock = load_package_lock()
    try:
        check_lock_environment(package_lock)
    except LockEnvironmentMismatch:
        pytest.skip("Skipping because test environment does not support test's package.lock.json.")

    _main('install')

    run_process = subprocess.run(
        [
            './venv/bin/python', '-c',
            'import aiohttp; print(aiohttp.__version__)',
        ],
        stdout=subprocess.PIPE,
    )
    output = run_process.stdout.decode('utf-8').strip()
    assert output == '3.1.3'
