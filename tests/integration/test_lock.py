from pathlib import Path
import json

import pytest

from dotlock.package_json import PackageJSON
from dotlock.package_lock import package_lock_data


@pytest.mark.asyncio
async def test_lock():
    testfile_path = str(Path(__file__).parent / Path('package.json'))
    package_json = PackageJSON.load(testfile_path)

    await package_json.resolve(update=False)

    lock_data = package_lock_data(package_json)

    # Check that the various build env attributes are present
    assert lock_data['python']
    assert lock_data['abi']
    assert lock_data['platform']
    assert lock_data['manylinux1'] is not None

    default_packages = {package['name'] for package in lock_data['default']}
    test_packages = {package['name'] for package in lock_data['extras']['tests']}

    assert default_packages == {
        'chardet',
        'async-timeout',
        'multidict',
        'idna',
        'attrs',
        'yarl',
        'aiohttp',
    }
    assert test_packages == default_packages | {
        'pytest',
        'pytest-aiohttp',
        'pluggy',
        'py',
        'setuptools',
        'six',
    }
