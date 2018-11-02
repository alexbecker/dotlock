#!/bin/bash
# Script for installing dependencies from bundle.tar.gz.
set -e
tar -xf bundle.tar.gz
python3 -m venv ./venv
ls bundle | xargs -I {} ./venv/bin/python -m pip install --no-index --no-deps bundle/{}
