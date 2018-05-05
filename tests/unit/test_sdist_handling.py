from pathlib import Path
import shutil

import pytest
from packaging.specifiers import SpecifierSet

from dotlock.dist_info_parsing import RequirementInfo
from dotlock.sdist_handling import get_sdist_file_requirements
from dotlock.tempdir import temp_working_dir


@pytest.mark.asyncio
async def test_get_wheel_file_requirements():
    idna_ssl_archive_name = 'idna-ssl-1.0.1.tar.gz'
    idna_ssl_archive_path = str(Path(__file__).parent / Path(idna_ssl_archive_name))

    with temp_working_dir():
        # Copy idna-ssl archive to a temporary directory like we download it to in sdist_handling.py
        shutil.copy(idna_ssl_archive_path, '.')
        idna_ssl_archive_path = str(Path('.') / Path(idna_ssl_archive_name))

        requirements = await get_sdist_file_requirements('idna-ssl', idna_ssl_archive_path)

    assert requirements == [
        RequirementInfo(name='idna', specifier=SpecifierSet('>=2.0'), extra=None, marker=None)
    ]
