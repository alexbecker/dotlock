from pathlib import Path
import shutil

import pytest

from dotlock.dist_info.dist_info import RequirementInfo
from dotlock.dist_info.sdist_handling import extract_file, get_local_package_requirements
from dotlock.tempdir import temp_working_dir


@pytest.mark.asyncio
async def test_get_wheel_file_requirements():
    idna_ssl_archive_name = 'idna-ssl-1.0.1.tar.gz'
    idna_ssl_archive_path = str(Path(__file__).parent / Path(idna_ssl_archive_name))

    with temp_working_dir():
        # Copy idna-ssl archive to a temporary directory like we download it to in sdist_handling.py
        shutil.copy(idna_ssl_archive_path, '.')
        idna_ssl_archive_path = str(Path('.') / Path(idna_ssl_archive_name))

        package_path = await extract_file(idna_ssl_archive_path)
        requirements = get_local_package_requirements('idna-ssl', package_path)

    assert requirements == [
        RequirementInfo.from_specifier_or_vcs('idna', '>=2.0'),
    ]
