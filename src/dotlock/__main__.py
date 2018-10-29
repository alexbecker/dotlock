import argparse
import asyncio
import logging
import sys
from typing import NoReturn

from dotlock.bundle import bundle
from dotlock.env import dump
from dotlock.exceptions import LockEnvironmentMismatch
from dotlock.graph import graph_resolution
from dotlock.package_json import PackageJSON
from dotlock.package_lock import write_package_lock, load_package_lock, check_lock_environment, get_locked_candidates
from dotlock.init import init
from dotlock.install import install
from dotlock.install_skip_lock import install_skip_lock
from dotlock.run import run


base_parser = argparse.ArgumentParser(description='A Python package management utility.')
base_parser.add_argument('--debug', action='store_true', default=False)
base_parser.add_argument('command', choices=['init', 'run', 'graph', 'lock', 'install', 'bundle', 'dump-env'])
base_parser.add_argument('args', nargs=argparse.REMAINDER, help='(varies by command)')

init_parser = argparse.ArgumentParser(
    prog='dotlock init',
    description='Creates a virtualenv (./venv) and default package.json.',
)

run_parser = argparse.ArgumentParser(
    prog='dotlock run',
    description='Runs a command within the virtualenv.',
)
run_parser.add_argument('command', help='command to run within the virtualenv')
run_parser.add_argument('args', nargs=argparse.REMAINDER, help='arguments to [command]')

graph_parser = argparse.ArgumentParser(
    prog='dotlock graph',
    description='Prints the dependency tree of package.lock.',
)
graph_parser.add_argument('--update', action='store_true', default=False)

lock_parser = argparse.ArgumentParser(
    prog='dotlock lock',
    description='Update package.lock.json.',
)
lock_parser.add_argument('--update', action='store_true', default=False)

install_parser = argparse.ArgumentParser(
    prog='dotlock install',
    description='Install dependencies from package.lock.json.',
)
install_parser.add_argument(
    '--skip-lock', action='store_true', default=False,
    help='Install dependencies directly from package.json instead of package.lock.json.',
)
install_parser.add_argument('--extras', nargs='+', default=[])
install_parser.add_argument(
    '--only', nargs='+',
    help='Only install the listed packages. Useful when upgrading individual packages.',
)

bundle_parser = argparse.ArgumentParser(
    prog='dotlock bundle',
    description='Bundle dependencies into a bundle.tar.gz file that can be installed with install.sh.',
)
bundle_parser.add_argument('--extras', nargs='+', default=[])

dump_env_parser = argparse.ArgumentParser(
    prog='dotlock dump-env',
    description='Write the current environment out to env.json.',
)


def _main(*args) -> int:
    logging.basicConfig()
    logger = logging.getLogger('dotlock')

    base_args = base_parser.parse_args(args)
    command = base_args.command
    args = base_args.args

    if base_args.debug:
        logging.getLogger('dotlock').setLevel(logging.DEBUG)

    if command == 'init':
        init()
        return 0

    package_json = PackageJSON.load('package.json')
    loop = asyncio.get_event_loop()

    if command == 'run':
        run_args = run_parser.parse_args(args)
        run(run_args.command, run_args.args)
    if command == 'graph':
        graph_args = graph_parser.parse_args(args)

        future = package_json.resolve(update=graph_args.update)
        loop.run_until_complete(future)
        graph_resolution(package_json.default)
    if command == 'lock':
        lock_args = lock_parser.parse_args(args)

        future = package_json.resolve(update=lock_args.update)
        loop.run_until_complete(future)
        write_package_lock(package_json)
    if command == 'install':
        install_args = install_parser.parse_args(args)

        if install_args.skip_lock:
            install_skip_lock(package_json, install_args.extras, install_args.only)
        else:
            package_lock = load_package_lock()

            try:
                check_lock_environment(package_lock)
            except LockEnvironmentMismatch as e:
                logger.error(
                    'The current environment does not match the one used to generate package.lock.json. '
                    'The PEP425 tags do not match (%s "%s"!="%s"), '
                    'so the wrong bdist_wheel distributions would be installed. '
                    'Either re-lock in this environment, or bypass the lock file altogether using --skip-lock.',
                    e.env_key, e.env_value, e.locked_value,
                )
            candidates = get_locked_candidates(package_lock, install_args.extras, install_args.only)
            future = install(candidates)
            loop.run_until_complete(future)
    if command == 'bundle':
        bundle_args = bundle_parser.parse_args(args)

        package_lock = load_package_lock()
        # Don't check package lock, because we aren't installing.
        candidates = get_locked_candidates(package_lock, bundle_args.extras, None)
        future = bundle(candidates)
        loop.run_until_complete(future)
    if command == 'dump-env':
        dump_env_parser.parse_args(args)

        dump()

    return 0


def main() -> NoReturn:
    exit_code = _main(*sys.argv[1:])
    exit(exit_code)


if __name__ == '__main__':
    main()
