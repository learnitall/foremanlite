#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hold various foremanlite variables.

Be sure to sync with version in pyproject.toml
"""
import os

VERSION: str = "0.1.0"

# --- CLI ---
LOGFILE_NAME = "foremanlite.log"

# --- Config ---
# This are relative to the configuration directory
DATA_DIR = "data"  # directory containing files served to clients
GROUPS_DIR = "groups"  # directory containing MachineGroup definitions
EXEC_DIR = "exec"  # directory containing executables or their configs

# --- iPXE ---
# File names for different actions
# These need to be configured in the data directory
IPXE_DIR = "ipxe"
# endpoint first hit by machines, configured in dhcp
IPXE_START = os.path.join(IPXE_DIR, "boot.ipxe.j2")
IPXE_PROVISION = os.path.join(
    IPXE_DIR, "provision.ipxe"
)  # endpoint hit when provisioned
IPXE_PASSTHROUGH = os.path.join(
    IPXE_DIR, "pass.ipxe"
)  # endpoint hit when not provisioning

# --- BUTANE ---
BUTANE_VERSION = "v0.13.1"
BUTANE_EXEC = "butane"  # relative to EXEC_DIR
BUTANE_DIR = "butane"

# --- GUNICORN ---
GUNICORN_DEFAULT_CONFIG = "gunicorn_conf_default.py"
GUNICORN_CONFIG = "gunicorn_conf.py"
