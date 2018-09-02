from typing import Dict, Iterable, Tuple, List
import json

from dotlock.resolve import PackageType, RequirementInfo, Requirement, resolve_requirements_list


def parse_requirements(requirement_dicts: Dict[str, str]) -> Tuple[Requirement, ...]:
    return tuple(
        Requirement(
            info=RequirementInfo.from_specifier_or_vcs(name, specifier),
            parent=None,
        ) for name, specifier in requirement_dicts.items()
    )


class PackageJSON:
    def __init__(
            self,
            sources: List[str],
            default: Iterable[Requirement],
            extras: Dict[str, Tuple[Requirement, ...]],
    ) -> None:
        self.sources = sources
        self.default = tuple(default)
        self.extras = extras

    @staticmethod
    def load(file_path: str) -> 'PackageJSON':
        with open(file_path) as fp:
            contents = json.load(fp)

        return PackageJSON(
            sources=contents['sources'],
            default=parse_requirements(contents['default']),
            extras={
                key: parse_requirements(reqs)
                for key, reqs in contents['extras'].items()
            },
        )

    async def resolve(self, update: bool) -> None:
        # Resolve for all extras simultaneously to prevent conflicts.
        requirements = list(self.default)
        for reqs in self.extras.values():
            requirements.extend(reqs)

        # Since resolve_requirements_list sets each Requirement's candidates,
        # and we did not deep copy when building the requirements list, this
        # modifies every Requirement in self.default and self.extras.
        await resolve_requirements_list(
            package_types=[PackageType.bdist_wheel, PackageType.sdist],  # FIXME: this is pretty arbitrary
            sources=self.sources,
            requirements=requirements,
            update=update,
        )
