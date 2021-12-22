#!/bin/bash
# Build foremanlite container
# Be sure to execute from root
set -xe

version=`python -m foremanlite.cli version`
podman build . -t foremanlite:$version
