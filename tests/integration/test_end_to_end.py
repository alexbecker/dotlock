import json
import subprocess

from dotlock.__main__ import _main
from dotlock.tempdir import temp_working_dir


def test_requests():
    with temp_working_dir():
        assert _main('init') == 0

        with open('package.json') as fp:
            package_json = json.load(fp)

        package_json['default']['requests'] = '==2.18.4'
        with open('package.json', 'w') as fp:
            json.dump(package_json, fp)

        assert _main('lock') == 0
        assert _main('install') == 0

        # We have to run "run" in a subprocess so it doesn't hijack test execution.
        run_process = subprocess.run(
            ['dotlock', 'run', 'python', '-c', 'import requests; print(requests.__version__)'],
            stdout=subprocess.PIPE,
        )

        output = run_process.stdout.decode('utf-8').strip()
        assert output == '2.18.4'
