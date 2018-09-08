import argparse
import asyncio
import logging
import sys
from typing import NoReturn

from dotlock.exceptions import LockEnvironmentMismatch
from dotlock.graph import graph_resolution
from dotlock.package_json import PackageJSON
from dotlock.package_lock import write_package_lock, load_package_lock, merge_candidate_lists
from dotlock.init import init
from dotlock.install import install
from dotlock.run import run


base_parser = argparse.ArgumentParser(description='A Python package management utility.')
base_parser.add_argument('--debug', action='store_true', default=False)
base_parser.add_argument('command', choices=['init', 'run', 'graph', 'lock', 'install'])
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
install_parser.add_argument('--extras', nargs='+', default=[])


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

        try:
            package_lock = load_package_lock('package.lock.json')
        except LockEnvironmentMismatch as e:
            logger.error('package.lock.json was generated with %s %s, but you are using %s',
                         e.env_key, e.locked_value, e.env_value)
            return -1

        default_reqs = package_lock['default']
        extras_reqs = [package_lock['extras'][extra] for extra in install_args.extras]
        candidates = merge_candidate_lists([default_reqs] + extras_reqs)

        future = install(candidates)
        loop.run_until_complete(future)

    return 0


def main() -> NoReturn:
    exit_code = _main(*sys.argv[1:])
    exit(exit_code)


if __name__ == '__main__':
    main()
