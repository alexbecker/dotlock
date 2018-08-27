import json
import subprocess

import pytest

from dotlock.__main__ import _main
from dotlock.tempdir import temp_working_dir


@pytest.mark.parametrize('source,spec,version', [
    ('https://pypi.org/pypi', '==2.18.4', '2.18.4'),
    ('https://pypi.org/simple', '==2.18.3', '2.18.3'),
    ('https://pypi.org/pypi', 'git+git://github.com/requests/requests@v2.19.1', '2.19.1')
])
def test_requests(source, spec, version):
    with temp_working_dir('test'):
        assert _main('init') == 0

        with open('package.json') as fp:
            package_json = json.load(fp)

        package_json['sources'] = [source]
        package_json['default'] = {'requests': spec}
        with open('package.json', 'w') as fp:
            json.dump(package_json, fp)

        # Use --update to bypass the cache.
        assert _main('lock', '--update') == 0
        assert _main('install') == 0

        # We have to run "run" in a subprocess so it doesn't hijack test execution.
        run_process = subprocess.run(
            [
                'dotlock', 'run', 'python', '-c',
                f'import requests; print(requests.__version__)',
            ],
            stdout=subprocess.PIPE,
        )

        output = run_process.stdout.decode('utf-8').strip()
        assert output == version
