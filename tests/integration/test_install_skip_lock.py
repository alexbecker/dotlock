import json
import subprocess

import pytest

from dotlock.__main__ import _main
from tests import test_path


@pytest.mark.parametrize('name,spec,version', [
    ('requests', '==2.18.4', '2.18.4'),
    ('requests', 'git+git://github.com/requests/requests@v2.19.1', '2.19.1'),
    ('fakepkg', str(test_path / 'fakepkg'), '1.2.3'),
])
def test_install_skip_lock(name, spec, version, tempdir):
    assert _main('init') == 0

    with open('package.json') as fp:
        package_json = json.load(fp)

    package_json['default'] = {name: spec}
    with open('package.json', 'w') as fp:
        json.dump(package_json, fp)

    assert _main('install', '--skip-lock') == 0

    # We have to run "run" in a subprocess so it doesn't hijack test execution.
    run_process = subprocess.run(
        [
            'dotlock', 'run', 'python', '-c',
            f'import {name}; print({name}.__version__)',
        ],
        stdout=subprocess.PIPE,
    )

    output = run_process.stdout.decode('utf-8').strip()
    assert output == version
