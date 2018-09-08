import logging
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from dotlock.dist_info.dist_info import RequirementInfo, CandidateInfo, PackageType
from dotlock.markers import Marker
from dotlock._vendored.appdirs import user_cache_dir
from dotlock._vendored.pep425tags import get_impl_tag, get_abi_tag, get_platform, is_manylinux1_compatible


logger = logging.getLogger(__name__)

setup_script_path = Path(__file__).parent / Path('cache_schema.sql')
with setup_script_path.open() as fp:
    setup_script = fp.read()


def cache_filename():
    schema_version = '0.3'
    impl = get_impl_tag()
    abi = get_abi_tag()
    platform = get_platform()
    manylinux1 = '-manylinux1' if is_manylinux1_compatible() else ''
    return f'cache-{schema_version}-{impl}-{abi}-{platform}{manylinux1}.sqlite'


def connect_to_cache():
    cache_dir = Path(user_cache_dir('dotlock'))
    if not cache_dir.exists():
        cache_dir.mkdir()

    cache_db_path = cache_dir / Path(cache_filename())
    exists = cache_db_path.exists()
    conn = sqlite3.connect(str(cache_db_path))

    if not exists:
        conn.executescript(setup_script)

    return conn


def get_cached_candidate_infos(
        connection: sqlite3.Connection,
        name: str,
) -> Optional[List[CandidateInfo]]:
    query = connection.execute(
        'SELECT name, version, package_type, source, url, hash_alg, hash_val FROM candidate_infos WHERE name=?',
        (name,)
    )
    results = [
        CandidateInfo(
            name=row[0],
            version=Version(row[1]),
            package_type=PackageType[row[2]],
            source=row[3],
            url=row[4],
            vcs_url=None,
            hash_alg=row[5],
            hash_val=row[6],
        ) for row in query.fetchall()
    ]

    if results:
        logger.debug('Cache HIT for candidate_infos %s', name)
        return results

    logger.debug('Cache MISS for candidate_infos %s', name)
    return None


def set_cached_candidate_infos(
        connection: sqlite3.Connection,
        candidate_infos: Iterable[CandidateInfo],
):
    for c in candidate_infos:
        connection.execute(
            'INSERT INTO candidate_infos (name, version, package_type, source, url, hash_alg, hash_val, requirements_cached) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                c.name,
                str(c.version),
                c.package_type.name,
                c.source,
                c.url,
                c.hash_alg,
                c.hash_val,
                False,
            )
        )
    connection.commit()


def get_cached_requirement_infos(
        connection: sqlite3.Connection,
        candidate_info: CandidateInfo,
) -> Optional[List[RequirementInfo]]:
    query = connection.execute(
        'SELECT requirements_cached FROM candidate_infos WHERE hash_val=?',
        (candidate_info.hash_val,)
    )
    result = query.fetchone()
    if result is None:  # No such candidate is cached.
        return None
    requirements_cached = result[0]
    if not requirements_cached:
        logger.debug('Cache MISS for requirement_infos %s', candidate_info)
        return None

    logger.debug('Cache HIT for requirement_infos %s', candidate_info)
    query = connection.execute(
        'SELECT name, vcs_url, specifier, extras, marker FROM requirement_infos '
        'WHERE candidate_hash=?',
        (candidate_info.hash_val,)
    )
    return [
        RequirementInfo(
            name=name,
            vcs_url=vcs_url,
            specifier=None if (vcs_url or specifier == '*') else SpecifierSet(specifier),
            extras=tuple(extras.split(',')) if extras else tuple(),
            marker=marker and Marker(marker),
        ) for (name, vcs_url, specifier, extras, marker) in query.fetchall()
    ]


def set_cached_requirement_infos(
        connection: sqlite3.Connection,
        candidate_info: CandidateInfo,
        requirement_infos: Iterable[RequirementInfo],
):
    for r in requirement_infos:
        connection.execute(
            'INSERT INTO requirement_infos (candidate_hash, name, vcs_url, specifier, extras, marker) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (
                candidate_info.hash_val,
                r.name,
                r.vcs_url,
                str(r.specifier) if r.specifier else '*',
                ','.join(r.extras) if r.extras else None,
                r.marker and str(r.marker),
            )
        )
    connection.execute(
        'UPDATE candidate_infos SET requirements_cached=1 WHERE hash_val=?',
        (candidate_info.hash_val,)
    )
    connection.commit()
