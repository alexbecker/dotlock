from typing import List

from package.resolve import Requirement


def graph_resolution(requirements: List[Requirement], offset=0):
    for requirement in requirements:
        for candidate in requirement.candidates.values():
            if candidate.live:
                print(offset * ' ' + f'{requirement.info}: {candidate.info.version} [{candidate.info.package_type.name}]')
                graph_resolution(candidate.requirements.values(), offset + 2)
