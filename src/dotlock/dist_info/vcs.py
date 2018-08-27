import asyncio
from typing import List

from dotlock.dist_info.dist_info import CandidateInfo
from dotlock.dist_info.sdist_handling import get_local_package_requirements
from dotlock.exceptions import VCSException
from dotlock.tempdir import temp_working_dir


def clone_command(vcs_url: str) -> List[str]:
    vcs_type, url = vcs_url.split('+')
    if '@' in url:
        url, tag = url.split('@')
        return {
            'git': ['git', 'clone', '--branch', tag, url]
        }[vcs_type]
    return {
        'git': ['git', 'clone', url]
    }[vcs_type]


async def get_vcs_requirement_infos(candidate_info: CandidateInfo):
    assert candidate_info.vcs_url
    with temp_working_dir():
        subprocess = await asyncio.create_subprocess_exec(
            *clone_command(candidate_info.vcs_url)
        )
        return_code = await subprocess.wait()
        if return_code != 0:
            raise VCSException(f'clone failed for {candidate_info.vcs_url}')

        clone_name_with_ext_and_tag = candidate_info.vcs_url.split('/')[-1]
        clone_name_with_ext = clone_name_with_ext_and_tag.split('@')[0]
        clone_dir_name = clone_name_with_ext.split('.')[0]
        return get_local_package_requirements(candidate_info.name, clone_dir_name)
