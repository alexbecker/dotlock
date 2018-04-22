from collections import defaultdict
from typing import List, Optional

from packaging.specifiers import Specifier
from packaging.version import Version


def prev_version(version: Version) -> Version:
    parts = [int(p) for p in str(version).split('')]
    non_zero_indices = [i for i, p in enumerate(parts) if p > 0]
    if not non_zero_indices:
        raise ValueError()
    parts[non_zero_indices[-1]] -= 1
    return Version('.'.join(str(p) for p in parts))


def max_satisfying_version(specifiers: List[Specifier]) -> Optional[Version]:
    if any(s.version.is_prerelease and s.operator != '==' for s in specifiers):
        raise ValueError('Pre-release versions are only supported with ==')

    versions_by_op = defaultdict(list, **{
        op: list(sorted({s.version for s in specifiers if s.operator == op}))
        for op in ['>', '>=', '<', '<=', '==', '~=', '!=']
    })
    if versions_by_op['==']:
        if len(specifiers) > 1:
            raise ValueError('== cannot be combined with other specifiers')
        return specifiers[0].version
    if versions_by_op['<=']:
        return versions_by_op['<='][0]
    elif versions_by_op['<']:
        version = versions_by_op['<']
        return prev_version(version)
    elif versions_by_op['~=']:
        pass #TODO
