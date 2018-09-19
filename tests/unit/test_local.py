from dotlock.dist_info.sdist_handling import get_local_package_requirements
from tests import test_path


def test_local():
    requirements = get_local_package_requirements('fakepkg', str(test_path / 'fakepkg'))
    assert [r.name for r in requirements] == ['aiohttp']
