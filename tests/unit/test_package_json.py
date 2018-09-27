from dotlock.dist_info.dist_info import RequirementInfo, SpecifierSet, SpecifierType
from dotlock.package_json import PackageJSON


def test_parse():
    parsed = PackageJSON.parse({
        'sources': [
            'https://pypi.org/pypi'
        ],
        'default': {
            'requests': '==18.1.3',
            'aiohttp': '<=3.0.0,>=2.3.1',
            'flask': 'git+git://github.com/flask/flask@v1.0.0',
            'mypackage': '.',
            'myotherpackage': '/home/me/project/myotherpackage',
        },
        'extras': {
            'tests': {
                'pytest': '*',
            }
        }
    })
    assert parsed.sources == [
        'https://pypi.org/pypi'
    ]
    assert len(parsed.default) == 5
    assert len(parsed.extras['tests']) == 1
