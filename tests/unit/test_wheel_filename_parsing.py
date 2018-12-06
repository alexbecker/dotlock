import pytest

from dotlock.dist_info import wheel_filename_parsing


@pytest.mark.parametrize(
    ('wheel', 'supported'), [
        ('matplotlib-3.0.2-cp37-cp37m-manylinux1_x86_64.whl', True),
        ('matplotlib-3.0.2-cp36-cp36m-manylinux1_x86_64.whl', False),
        ('matplotlib-3.0.2-cp27-cp27m-manylinux1_x86_64.whl', False),
        ('matplotlib-3.0.2-cp37-cp37m-macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64.macosx_10_10_intel.macosx_10_10_x86_64.whl', False),
        ('matplotlib-3.0.2-pp35-pypy_41-manylinux1_x86_64.whl', False),
        ('matplotlib-3.0.2-cp37-cp37m-win32.whl', False),
        ('matplotlib-3.0.2-py3-none-any.whl', True),
        ('matplotlib-3.0.2-py2-none-any.whl', False),
        ('matplotlib-3.0.2-py2.py3-none-any.whl', True),
    ]
)
def test_is_supported_cp37_manylinux1_x86_64(monkeypatch, wheel, supported):
    monkeypatch.setattr(wheel_filename_parsing, 'pep425tags', {
        'abi': 'cp37m',
        'impl': 'cp',
        'manylinux1': True,
        'platform': 'linux_x86_64',
        'version': '3.7'
    })

    assert wheel_filename_parsing.is_supported(wheel) is supported
