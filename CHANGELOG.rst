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

* Support `sha1` and `md5` package digests

* Concurrent package downloads during `dotlock install`

0.4.1 (2018-09-03)
------------------

* Support `svn://` and `hg://` dependencies

* Fixes a bug in handling old sdists which use `requires` instead of `install_requires`

* Fixes a bug where extras dependencies were included in the `default` section of `package.lock.json`

* Explain an unfixable error encountered running `dotlock init` from within a virtualenv while using a copied system `python` installation

0.4.0 (2018-09-01)
------------------

* Support PEP 503 "Simple" APIs, not just the non-standard PyPI JSON API

* Support `git://` dependencies

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
