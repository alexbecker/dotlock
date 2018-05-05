from typing import List
import json

from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from dotlock.resolve import PackageType, RequirementInfo, Requirement, resolve_requirements_list


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
                Requirement(
                    info=RequirementInfo(
                        name=canonicalize_name(name),
                        specifier=SpecifierSet(specifier) if specifier != '*' else None,
                        extra=None,
                        marker=None,
                    ),
                    parent=None,
                ) for name, specifier in contents['default'].items()
            ],
        )

    async def resolve_default(self):
        return await resolve_requirements_list(
            package_types=[PackageType.bdist_wheel, PackageType.sdist],  # FIXME: this is pretty arbitrary
            sources=self.sources,
            requirements=self.default,
        )
