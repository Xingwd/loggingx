#!/usr/bin/env bash

release_to_pypi=$1

if [ "$release_to_pypi" = "1" ]; then
    repository="pypi"
else
    repository="testpypi"
fi
echo "release to $repository"

python -m pip install --upgrade build
python -m build
python -m pip install --upgrade twine
python -m twine upload --verbose --repository $repository dist/*
