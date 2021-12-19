#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable-all
"""
Get butane executable.

Reads target butane version (BUTANE_VERSION) and filename
(BUTANE_EXEC) from foremanlite.vars module. Will then reach
out to butane's release page on github to download
and save the executable.

Only required argument is destination path. Can give architecture
and platform as optional arguments.
"""
import argparse
import enum
import os
import urllib.request

from foremanlite.vars import BUTANE_EXEC, BUTANE_VERSION


class Architecture(enum.Enum):
    aarch64 = "aarch64"
    ppc64le = "ppc64le"
    s390x = "s390x"
    x86_64 = "x86_64"


class Platform(enum.Enum):
    linux = "unknown-linux-gnu"
    windows = "pc-windows.exe"
    osx = "apple-darwin"


BASE_URL = "https://github.com/coreos/butane/releases/download"


def validate_dest(dest: str):
    if not os.path.exists(dest):
        raise ValueError(f"Given destination does not exist: {dest}")
    elif not os.path.isdir(dest):
        raise ValueError(f"Given destination is not a directory: {dest}")
    elif not os.access(dest, os.W_OK):
        raise ValueError(f"Unable to write to given destination: {dest}")


def download(url: str, dest: str):
    print(f"Downloading {url} to {dest}")
    urllib.request.urlretrieve(url, dest)


def main(version: str, dest: str, arch: Architecture, platform: Platform):
    target_url = f"{BASE_URL}/{version}/butane-{arch.value}-{platform.value}"
    target_path = os.path.join(dest, BUTANE_EXEC)

    download(target_url, target_path)
    os.chmod(target_path, 0o744)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dest")
    parser.add_argument(
        "--arch",
        choices=(a.value for a in Architecture),
        default=Architecture.x86_64,
    )
    parser.add_argument(
        "--platform",
        choices=(p.value for p in Platform),
        default=Platform.linux,
    )
    result = parser.parse_args()

    main(
        dest=result.dest,
        version=BUTANE_VERSION,
        arch=result.arch,
        platform=result.platform,
    )
