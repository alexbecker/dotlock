import json
import subprocess

import pytest

from dotlock.__main__ import _main
from dotlock.tempdir import temp_working_dir


@pytest.mark.parametrize('source,package_name,package_version', [
    ('https://pypi.org/pypi', 'requests', '2.18.4'),
    ('https://pypi.org/simple', 'requests', '2.18.3'),
])
def test_single_package(source, package_name, package_version):
    with temp_working_dir():
        import logging; logging.getLogger('dotlock').setLevel(logging.DEBUG)
        assert _main('init') == 0

        with open('package.json') as fp:
            package_json = json.load(fp)

        package_json['sources'] = [source]
        package_json['default'][package_name] = f'=={package_version}'
        with open('package.json', 'w') as fp:
            json.dump(package_json, fp)

        # Use --update to bypass the cache.
        assert _main('lock', '--update') == 0
        assert _main('install') == 0

        # We have to run "run" in a subprocess so it doesn't hijack test execution.
        run_process = subprocess.run(
            [
                'dotlock', 'run', 'python', '-c',
                f'import {package_name}; print({package_name}.__version__)',
            ],
            stdout=subprocess.PIPE,
        )

        output = run_process.stdout.decode('utf-8').strip()
        assert output == package_version
