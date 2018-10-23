from pathlib import Path
import json

from dotlock import env


def test_load_current_env():
    env.load()
    assert env.environment
    assert env.pep425tags


def test_dump_current_env(tempdir):
    env.dump()
    assert Path('env.json').exists()


def test_load_from_file(tempdir):
    new_env = {
        "environment": {
            "implementation_name": "cpython",
            "implementation_version": "3.5.0",
            "os_name": "posix",
            "platform_machine": "i386",
            "platform_python_implementation": "CPython",
            "platform_release": "4.17.14-arch1-1-ARCH",
            "platform_system": "Linux",
            "platform_version": "#1 SMP PREEMPT Thu Aug 9 11:56:50 UTC 2018",
            "python_full_version": "3.5.0",
            "python_version": "3.5",
            "sys_platform": "linux"
        },
        "pep425tags": {
            "abi": "cp35m",
            "impl": "cp35",
            "manylinux1": True,
            "platform": "linux_i386",
            "version": "3.5"
        }
    }
    with Path('env.json').open('w') as fp:
        json.dump(new_env, fp)

    env.load()
    assert env.environment == new_env['environment']
    assert env.pep425tags == new_env['pep425tags']
