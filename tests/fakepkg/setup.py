from setuptools import find_packages, setup


setup(
    name='fakepkg',
    version='1.2.3',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'aiohttp',
    ],
    extras_require={
        'tests': [
            'pytest'
        ]
    },
)
