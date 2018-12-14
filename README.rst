dotlock
=======

.. image:: https://travis-ci.org/alexbecker/dotlock.svg?branch=master
    :target: https://travis-ci.org/alexbecker/dotlock

Fast and safe dependency management for Python applications.

Supports Linux and OS X.

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
dependency-locking functionality. However, dotlock has a different philosophy: instead of acting as a wrapper
around pip, dotlock handles package resolution natively. This gives dotlock more flexibility, better performance,
and a smaller surface area for bugs, but at the cost of the wide platform and package support the pip developers have
put so much work into. This should make dotlock better for deploying to common environments such as linux servers
with common packages, but there will always be edge cases of platforms or packages it does not support.

Dotlock's main goals are:

* Accuracy: ``dotlock lock`` locks to the level of specific distributions, not just versions.
  That means you know exactly what code will be installed by ``dotlock install``, and ``package.lock.json``
  will contain a single hash for each package. You can even vendor your dependencies with ``dotlock bundle``.

* Speed: ``dotlock lock`` uses caching and asyncio to re-lock after changes to ``package.lock`` in 1s or less.
  Similarly, ``dotlock install`` and ``dotlock bundle`` download dependencies in parallel.

* Extras Support: Unlike pipenv which only supports "default" dependencies and "dev" dependencies,
  ``dotlock`` supports arbitrary extra dependency groups, e.g. ``dotlock install --extras tests``.

Installation
------------

Dotlock can be installed with ``pip``, i.e. ``pip install dotlock``.
It can be installed in an application's virtual environment, at the user level, or globally.

Development Setup
-----------------

On your development machine, run ``dotlock init`` to create a virtualenv and a skeleton ``package.lock`` file.
Add your sources and dependencies to ``package.lock``:

.. code-block:: javascript

    {
        "sources": [
            // PyPI-like package index hosting the dependencies.
            // If multiple indexes are included, each is tried in order during dependency resolution.
            "https://pypi.org/pypi"
        ],
        "default": {
            // Requirements in the form "package-name": "specifier".
            // Version specifiers may be "*", or a version number preceded by any of <, <=, >, >=, or ==.
            // Multiple specifiers can be separated by commas, e.g. ">=2.1,<3.0".
            "setuptools": ">=39.0",
            "virtualenv": "*",
            // Git, Mercurial and Subversion dependencies are also supported.
            "requests": "git+git://github.com/requests/requests@v2.19.1",
            // If you need extras or markers, supply a dictionary instead of a string.
            "idna_ssl": {
                "specifier": "*",
                "marker": "python_version < 3.7",  // See PEP 496
                "extras": ["tests"],
            },
            // Local file paths can be used too, but this loses integrity guarantees.
            "mypackage": "~/projects/mypackage"
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

Then you can lock and install your dependencies:

.. code-block:: shell

    dotlock lock  # Creates package.lock.json.
    dotlock install  # Installs exactly the distributions in package.lock.json.
    # Either source venv/bin/activate to enter the virtualenv, or use dotlock run.
    dotlock run [program] [args]  # Runs [program] in the virtualenv.

For more information, run ``dotlock -h`` or ``dotlock [command] -h``.

Developing in Different Environments
------------------------------------

If your development environment differs significantly from your target deployed environment,
e.g. you use a different operating system or a different version of Python, you will have to
do some extra work and lose some of the benefits of ``dotlock``.

In order to resolve dependencies and select distributions correctly, ``dotlock`` needs to know
certain features of the deployed environment. Run ``dotlock dump-env`` on the deployed environment
to create an ``env.json`` file. This file should live alongside your ``package.json`` file, and
will be used by ``dotlock lock``.

Since ``package.lock.json`` contains only the distributions appropriate for your deployed environment,
running ``dotlock install`` on an incompatible environment will error. Instead, you can run
``dotlock install --skip-lock``, which will bypass ``package.lock.json``, looking just at ``package.json``.

Deployment
----------

There are two ways to install your locked dependencies during deployment:

* Install ``dotlock`` and run ``dotlock install`` in the application root directory.

* Use ``dotlock bundle`` to create ``bundle.tar.gz`` and ``install.sh`` prior to deployment,
  include these files in the deployment, and run ``./install.sh`` during deployment.

Using ``dotlock bundle`` is preferred because it does not require installing ``dotlock`` in
the deployed environment and does not depend on external services during deploy.

Once the dependencies are installed, run your application with one of:

* ``source venv/bin/activate; [program] [args]``

* Assuming ``dotlock`` is installed: ``dotlock run [program] [args]``

Roadmap and Limitations
-----------------------

Planned features:

* Interpolate environment variables in ``sources``

* Allow specifying indices for individual packages

Features under consideration:

* Support virtualenvs other than ``./venv``

* Support installing into system python (useful in certain contexts, e.g. containers)

* Support versions of Python before 3.6

* Support locking for other platforms. This is not possible to do with perfect reliability,
  since the dependencies discovered by running ``setup.py`` may differ depending on what
  platform the script is run on.
