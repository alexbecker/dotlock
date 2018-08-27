import os
from typing import NoReturn

from pathlib import Path


def run(path, args) -> NoReturn:
    venv_script = Path('venv/bin/activate_this.py')
    with open(venv_script) as fp:
        exec(fp.read(), {'__file__': venv_script})

    # exec* functions expect args[0] to contain the name of the program
    os.execlp(path, path, *args)
