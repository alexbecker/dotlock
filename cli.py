import argparse
import asyncio
import logging
import sys

from package.graph import graph_resolution
from package.package_json import PackageJSON
from package.package_lock import write_package_lock


base_parser = argparse.ArgumentParser(description='A Python package management utility.')
base_parser.add_argument('--debug', action='store_true', default=False)
base_parser.add_argument('command', choices=['graph', 'lock'])
base_parser.add_argument('args', nargs=argparse.REMAINDER, help='(varies by command)')


if __name__ == '__main__':
    logging.basicConfig()

    base_args = base_parser.parse_args(sys.argv[1:])
    command = base_args.command
    args = base_args.args

    if base_args.debug:
        logging.getLogger('package').setLevel(logging.DEBUG)

    package_json = PackageJSON.load('package.json')

    loop = asyncio.get_event_loop()

    if command == 'graph':
        future = package_json.resolve_default()
        loop.run_until_complete(future)
        graph_resolution(package_json.default)
    if command == 'lock':
        future = package_json.resolve_default()
        loop.run_until_complete(future)
        write_package_lock(package_json)
