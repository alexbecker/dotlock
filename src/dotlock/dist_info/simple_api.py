"""
For interfacing with the Simple Repository API specified in PEP 503.
"""
from html.parser import HTMLParser
from typing import List, Optional
from urllib.parse import urlparse, urldefrag, ParseResult
import logging
import sys
import re

from aiohttp import ClientSession
from packaging.version import Version
from packaging.specifiers import SpecifierSet

from dotlock.exceptions import UnsupportedHashFunctionError
from dotlock.dist_info.dist_info import CandidateInfo, PackageType
from dotlock.dist_info.wheel_filename_parsing import is_supported, get_wheel_version


logger = logging.getLogger(__name__)


class PackagePageHTMLParser(HTMLParser):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.urls: List[ParseResult] = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return

        attrs = dict(attrs)
        url = urlparse(attrs['href'])

        requires_python = attrs.get('data-requires-python')
        if requires_python:
            requires_python = requires_python.replace('&gt;', '>').replace('&lt;', '<')
            python_specifier = SpecifierSet(requires_python)
            python_version = Version('.'.join(str(n) for n in sys.version_info[:2]))
            if not python_specifier.contains(python_version):
                logger.debug('Skipping candidate for %s (requires python %s)', self.name, requires_python)
                return

        self.urls.append(url)

_SDIST_EXTS_RE = r'(\.tar\.gz|\.tar\.bz2|\.zip)'
_SDIST_FILENAME_RE = re.compile(r'(?P<name>[a-z0-9\-]+)-(?P<ver>(\d+\.)*\d+[a-z0-9]*)' + _SDIST_EXTS_RE)


async def get_candidate_infos(
        package_types: List[PackageType],
        source: str,
        session: ClientSession,
        name: str,
) -> Optional[List[CandidateInfo]]:
    index_url = f'{source}/{name}/'
    async with session.get(index_url) as response:
        if response.status == 404:
            return None
        response.raise_for_status()
        content = await response.text()

    parser = PackagePageHTMLParser(name)
    parser.feed(content)

    candidate_infos = []
    for candidate_url in parser.urls:
        if not candidate_url.fragment:
            raise UnsupportedHashFunctionError(hash_function=None)
        hash_function, hash_value = candidate_url.fragment.split('=')
        if hash_function != 'sha256':
            raise UnsupportedHashFunctionError(hash_function)

        filename = candidate_url.path.split('/')[-1]
        if filename.endswith('.whl'):
            package_type = PackageType.bdist_wheel
            if not is_supported(filename):
                logger.debug('Skipping unsupported bdist %s', filename)
                continue

            candidate_infos.append(CandidateInfo(
                name=name,
                version=get_wheel_version(filename),
                package_type=package_type,
                source=source,
                url=urldefrag(candidate_url.geturl()).url,  # Strip sha256= fragment.
                vcs_url=None,
                sha256=hash_value,
            ))
        else:
            package_type = PackageType.sdist

            parsed_filename = _SDIST_FILENAME_RE.match(filename)
            if not parsed_filename:
                logging.debug(f'Skipping unrecognized filename {filename}')
                continue

            candidate_infos.append(CandidateInfo(
                name=name,
                version=Version(parsed_filename.group('ver')),
                package_type=package_type,
                source=source,
                url=urldefrag(candidate_url.geturl()).url,  # Strip sha256= fragment.
                vcs_url=None,
                sha256=hash_value,
            ))

    return candidate_infos
