from setuptools import find_packages, setup


with open('src/dotlock/__init__.py') as fp:
    # defines __version__
    exec(fp.read())


with open('README.rst') as fp:
    README = fp.read()


setup(
    name='dotlock',
    version=__version__,
    author='Alex Becker',
    author_email='myself@alexcbecker.net',
    url='https://github.com/alexbecker/dotlock',
    description='Fast and accurate Python dependency management',
    long_description=README,
    license='MIT',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        'dotlock': [
            'dist_info/cache_schema.sql',
            'package.skeleton.json',
            'install.sh',
        ],
    },
    entry_points={
        'console_scripts': [
            'dotlock = dotlock.__main__:main'
        ],

    },
    install_requires=[
        'aiohttp>=3.1',
        'packaging',
        'pip>=10.0',
        'setuptools>=39.0',
        'six',
        'virtualenv',
    ],
    extras_require={
        'tests': [
            'pytest',
            'pytest-asyncio',
        ],
    },
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='packaging requirements dependencies',
)
