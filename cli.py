import argparse
import asyncio
import sys

from package.package_json import PackageJSON
from package.resolve import print_candidate_tree


base_parser = argparse.ArgumentParser(description='A Python package management utility.')
base_parser.add_argument('command', choices=['graph'])
base_parser.add_argument('args', nargs=argparse.REMAINDER, help='(varies by command)')


if __name__ == '__main__':
    base_args = base_parser.parse_args(sys.argv[1:])
    command = base_args.command
    args = base_args.args

    package_json = PackageJSON.load('package.json')

    loop = asyncio.get_event_loop()

    if command == 'graph':
        future = package_json.resolve_default()
        tree = loop.run_until_complete(future)
        print_candidate_tree(tree)
