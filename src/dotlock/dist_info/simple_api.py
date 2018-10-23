"""
For interfacing with the Simple Repository API specified in PEP 503.
"""
from html.parser import HTMLParser
from typing import List, Optional
from urllib.parse import urlparse, urldefrag, ParseResult, urljoin
import logging
import re

from aiohttp import ClientSession
from packaging.version import Version, InvalidVersion
from packaging.specifiers import SpecifierSet

from dotlock.env import pep425tags
from dotlock.exceptions import UnsupportedHashFunctionError
from dotlock.dist_info.dist_info import CandidateInfo, PackageType, hash_algorithms
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
            python_version = Version(pep425tags['version'])
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
        if candidate_url.hostname is None:
            # Convert the relative URL to an absolute URL
            candidate_url = urlparse(urljoin(source, candidate_url.geturl()))

        if not candidate_url.fragment:
            raise UnsupportedHashFunctionError(hash_function=None)
        hash_alg, hash_val = candidate_url.fragment.split('=')
        if hash_alg not in hash_algorithms:
            raise UnsupportedHashFunctionError(hash_alg)

        filename = candidate_url.path.split('/')[-1]

        try:
            if filename.endswith('.whl'):
                package_type = PackageType.bdist_wheel
                if not is_supported(filename):
                    logger.debug('Skipping unsupported bdist %s', filename)
                    continue

                version = get_wheel_version(filename)
            else:
                package_type = PackageType.sdist

                parsed_filename = _SDIST_FILENAME_RE.match(filename)
                if not parsed_filename:
                    logging.debug(f'Skipping unrecognized filename {filename}')
                    continue

                version = Version(parsed_filename.group('ver'))
        except InvalidVersion:
            logger.warning('Skipping invalid version for file %s', filename)
            continue

        candidate_infos.append(CandidateInfo(
            name=name,
            package_type=package_type,
            version=version,
            source=source,
            location=urldefrag(candidate_url.geturl()).url,  # Strip [hash_alg]= fragment.
            hash_alg=hash_alg,
            hash_val=hash_val,
        ))

    return candidate_infos
