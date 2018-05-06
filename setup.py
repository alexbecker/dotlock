from setuptools import setup


with open('dotlock/__init__.py') as fp:
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
    tests_require=[
        'pytest',
        'pytest-asyncio',
    ],
    py_modules=['dotlock'],
    install_requires=[
        'aiohttp>=3.1',
        'distlib',
        'packaging',
        'pip>=9.0',
        'setuptools>=39.0',
        'virtualenv',
    ],
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
