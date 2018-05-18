dotlock
=======

Bringing sanity to Python dependency management.

Motivation
----------

The de-facto standard way to keep track of Python dependencies is with a ``requirements.txt`` file,
listing the required packages and specifying what versions of them can be used.
There are two strategies for specifying versions in a ``requirements.txt`` file:
adding only the top-level dependencies and constraints you know to be necessary,
or adding every recursive dependency and pinning them to specific versions you know work.
The first strategy makes installing dependencies non-repeatable.
The second makes upgrading difficult, and is hard to manage with standard python tools.

Dotlock enables you to do both: keep track of top-level requirements and known constraints
in ``package.json``, and generate repeatable requirement sets in ``package.lock.json``
by running a single command: ``dotlock lock``.

Dotlock is partly inspired by `pipenv <https://pypi.org/project/pipenv/>`_, which also provides
dependency-locking functionality. However, dotlock attempts to improve over ``pipenv`` in
the following ways:

* Accuracy: ``pipenv`` only locks to the level of versions, not specific distributions.
  This is why a ``Pipfile.lock`` will often contain multiple hashes for the same dependency,
  and means you do not know exactly what distribution will be installed when you run ``pipenv lock``.

* Speed: ``pipenv lock`` is very slow in my experience.

* Reliability: ``pipenv`` does a lot of stuff, but it also has a lot of bugs.

* Extras Support: ``pipenv`` only supports "default" dependencies and "dev" dependencies;
  ``dotlock`` supports arbitrary extra dependency groups, e.g. ``dotlock install --extras tests``.

Under the hood, ``pipenv`` is essentially a complicated wrapper for ``pip``, relying on it
for metadata discovery and extraction, dependency resolution, dependency downloading and installation.
To improve on ``pipenv``, ``dotlock`` handles most of these itself, relying on ``pip`` only to install
already-downloaded dependencies.

Usage
-----

On your development machine, run:

.. code-block:: shell

    dotlock init  # Creates a virtualenv and skeleton package.lock.
    dotlock lock  # Generates a package.lock.json file from package.json.

Then on both development and deployed machines, run:

.. code-block:: shell

    dotlock install   # Installs exactly the distributions in package.lock.json.
    dotlock activate  # Enters the virtualenv.

For more information, run ``dotlock -h`` or ``dotlock [command] -h``.

package.json example
--------------------

.. code-block:: javascript

    {
        "sources": [
            // PyPI-like package index hosting the dependencies.
            // If multiple indexes are included, each is tried in order during dependency resolution.
            "https://pypi.org/pypi"
        ],
        "default": {
            // Requirements in the form "package-name": "specifier".
            // Specifiers may be "*", or a version number preceded by any of <, <=, >, >=, or ==.
            // Multiple specifiers can be separated by commas, e.g. ">=2.1,<3.0".
            "setuptools": ">=39.0",
            "virtualenv": "*"
        },
        "extras": {
            // You can specify groups of additional dependencies that will be installed by
            // dotlock install --extras [names]
            "dev": {
                "ipython": "*"
            },
            "tests": {
                "pytest": "*"
            }
        }
    }

Roadmap and Limitations
-----------------------

Planned features:

* Handle non-PyPI `PEP 503 <https://www.python.org/dev/peps/pep-0503/>`_ compliant package indices: target ``0.4.0``

* VCS dependencies (git, svn, hg): target ``0.4.0``

* Concurrent package downloads in ``dotlock install``: target ``0.4.0``

* CI testing: target ``0.4.0``

* Local dependencies: target ``0.5.0``

* Richer specifier support: target ``0.6.0``

* Comments in ``package.json``: target ``0.6.0``

* Support/CI testing on non-linux platforms: target ``1.0.0``

Features under consideration:

* Support virtualenvs other than ``./venv``

* Support versions of Python before 3.6

* Integration with ``wheelhouse`` or similar dependency-bundling functionality

Features you might want but are not planned:

* Support locking for other platforms. This is not possible to do with perfect reliability,
  since the dependencies discovered by running ``setup.py`` may differ depending on what
  platform the script is run on.
