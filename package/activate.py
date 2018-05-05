import os.path


def activate():
    venv_script = os.path.join('venv', 'bin', 'activate_this.py')
    with open(venv_script) as fp:
        exec(fp.read(), {'__file__': venv_script})
