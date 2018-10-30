import json
import os
import shutil
import subprocess

import pytest

from dotlock.__main__ import _main
from tests import test_path


def make_package_json(source, name, spec):
    assert _main('init') == 0

    with open('package.json') as fp:
        package_json = json.load(fp)

    package_json['sources'] = [source]
    package_json['default'] = {name: spec}

    with open('package.json', 'w') as fp:
        json.dump(package_json, fp)


@pytest.mark.parametrize('source,name,spec,version', [
    ('https://pypi.org/pypi', 'requests', '==2.18.4', '2.18.4'),
    ('https://pypi.org/simple', 'requests','==2.18.3', '2.18.3'),
    ('https://pypi.org/pypi', 'requests', 'git+git://github.com/requests/requests@v2.19.1', '2.19.1'),
    ('https://pypi.org/pypi', 'requests', 'svn+https://github.com/requests/requests/trunk@6920', '2.19.0'),
    ('https://pypi.org/pypi', 'distlib', 'hg+https://hg.python.org/distlib@0.1.7', '0.1.7'),
    ('https://pypi.org/pypi', 'fakepkg', str(test_path / 'fakepkg'), '1.2.3'),
])
def test_package(source, name, spec, version, tempdir):
    make_package_json(source, name, spec)

    # Use --update to bypass the cache.
    assert _main('lock', '--update') == 0
    assert _main('install') == 0

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


def test_bundle_and_install(tempdir):
    make_package_json('https://pypi.org/pypi', 'requests', '==2.18.4')

    assert _main('lock', '--update') == 0
    assert _main('bundle') == 0

    os.mkdir('deploy')
    shutil.move('bundle.tar.gz', 'deploy')
    shutil.move('install.sh', 'deploy')
    os.chdir('deploy')

    subprocess.run(['./install.sh'])
    run_process = subprocess.run(
        [
            './venv/bin/python', '-c',
            'import requests; print(requests.__version__)',
        ],
        stdout=subprocess.PIPE,
    )

    output = run_process.stdout.decode('utf-8').strip()
    assert output == '2.18.4'
