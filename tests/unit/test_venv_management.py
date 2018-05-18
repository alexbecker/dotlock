import subprocess

from dotlock.init import init
from dotlock.tempdir import temp_working_dir


def test_init_run():
    with temp_working_dir():
        init()

        # We have to run "run" in a subprocess so it doesn't hijack test execution.
        run_process = subprocess.run('dotlock run which python'.split(), stdout=subprocess.PIPE)

        output = run_process.stdout.decode('utf-8').strip()
        assert output.endswith('/venv/bin/python')
