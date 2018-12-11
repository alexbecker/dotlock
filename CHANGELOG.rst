0.7.5 (2018-12-10)
------------------

* Limit simultaneous connections on download, not just during resolution

* (fixed) Don't require ``package.json`` for commands that don't depend on it

0.7.4 (2018-12-09)
------------------

* (broken) Don't require ``package.json`` for commands that don't depend on it

0.7.3 (2018-12-08)
------------------

* Check index when pinned versions aren't in cache, instead of raising

* Reduce logging volume at default log level

0.7.2 (2018-12-06)
------------------

* Fix wheel compatibility checks, allowing more wheels to be installed

0.7.1 (2018-11-02)
------------------

* Fix builds for some packages including numpy

* Fix install.sh script produced by ``dotlock bundle``

0.7.0 (2018-10-28)
------------------

* Better support for developing on different environments

* CI testing for OS X

0.6.0 (2018-10-10)
------------------

* New ``--skip-lock`` flag for ``dotlock install``

* New ``dotlock bundle`` command

0.5.2 (2018-10-05)
------------------

* Support comments in ``package.json``

0.5.1 (2018-09-30)
------------------

* Support markers and extras in ``package.json``

0.5.0 (2018-09-19)
------------------

* Support local package requirements

* Fix script installs using wrong python executible

0.4.3 (2018-09-09)
------------------

This is a minor release to fix some bugs in simple API handling:

* Handle relative URLs

* Skip invalid version numbers instead of erroring out

0.4.2 (2018-09-08)
------------------

* Support ``sha1`` and ``md5`` package digests

* Concurrent package downloads during ``dotlock install``

0.4.1 (2018-09-03)
------------------

* Support ``svn://`` and ``hg://`` dependencies

* Fixes a bug in handling old sdists which use ``requires`` instead of ``install_requires``

* Fixes a bug where extras dependencies were included in the ``default`` section of ``package.lock.json``

* Explain an unfixable error encountered running ``dotlock init`` from within a virtualenv while using a copied system ``python`` installation

0.4.0 (2018-09-01)
------------------

* Support PEP 503 "Simple" APIs, not just the non-standard PyPI JSON API

* Support ``git://`` dependencies

0.3.0 (2018-05-18)
------------------

* Replace fatally flawed "activate" command with "run" command that works

* Mypy incorporated into tox tests; outstanding issues fixed

0.2.3 (2018-05-16)
------------------

* Change code layout for better testing

* Add tox testing

* Only use cached data for compatible environment

* Error on installs from lockfiles generated for incompatible environments
