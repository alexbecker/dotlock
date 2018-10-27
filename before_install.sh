#!/bin/bash
# Script for travis before_install setup.

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    export LDFLAGS="-L$(brew --prefix openssl)/lib" CFLAGS="-I$(brew --prefix openssl)/include"
    brew update
    brew upgrade python
    brew install mercurial subversion
else
    sudo apt-get update
    sudo apt-get install -y mercurial subversion
fi

pip install tox-travis
