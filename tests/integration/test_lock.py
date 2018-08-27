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

    golden_path = str(Path(__file__).parent / Path('package.lock.json'))
    with open(golden_path, 'r') as fp:
        golden_data = json.load(fp)

    assert lock_data == golden_data
