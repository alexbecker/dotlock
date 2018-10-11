import os
import subprocess
from typing import Iterable, Optional, Container

from dotlock.dist_info.dist_info import RequirementInfo, SpecifierType
from dotlock.package_json import PackageJSON


def pip_format_reqs(reqs: Iterable[RequirementInfo]):
    pip_args = []
    for req in reqs:
        if req.specifier_type == SpecifierType.path:
            pip_args.append('-e')
            pip_args.append(req.specifier)
        elif req.specifier_type == SpecifierType.vcs:
            pip_args.append(f'{req.specifier}#egg={req.name}')
        else:
            pip_args.append(f'{req.name}{req.specifier}')
    return pip_args


def install_skip_lock(package_json: PackageJSON, extras: Iterable[str], name_filter: Optional[Container[str]]):
    """
    This is a minimal wrapper around pip to install the dependencies in package.json.
    While it presents a similar API as install, it is completely different because
    it ignores the lockfile and uses package.json instead.
    """
    requirements = list(package_json.default)
    for extra in extras:
        requirements.extend(package_json.extras[extra])
    reqs = [
        requirement.info for requirement in requirements
        if name_filter is None or requirement.info.name in name_filter
    ]

    python_path = os.path.join(os.getcwd(), 'venv', 'bin', 'python')
    subprocess.run([python_path, '-m', 'pip', 'install', *pip_format_reqs(reqs)])
