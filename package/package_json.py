from typing import List
import json

from package.resolve import Requirement, get_candidate_tree, flatten_candidate_tree


class PackageJSON:
    def __init__(self, python_version: str, sources: List[str], default: List[Requirement]):
        self.python_version = python_version
        self.sources = sources
        self.default = default

    @staticmethod
    def load(file_path: str):
        with open(file_path) as fp:
            contents = json.load(fp)
        return PackageJSON(
            python_version=contents['python'],
            sources=contents['sources'],
            default=[
                Requirement(name, version if version != '*' else None, marker=None)
                for name, version in contents['default'].items()
            ],
        )

    async def resolve_default(self):
        return await get_candidate_tree(
            package_types=['bdist_wheel', 'sdist'],  # FIXME: this is pretty arbitrary
            python_version=self.python_version,
            extra='',
            sources=self.sources,
            requirements=self.default,
        )
