#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hold various foremanlite variables.

Be sure to sync with version in pyproject.toml
"""
VERSION: str = "0.1.0"

# --- CLI ---
LOGFILE_NAME = "foremanlite.log"

# --- Config ---
# This are relative to the configuration directory
DATA_DIR = "data"  # directory containing files served to clients
GROUPS_DIR = "groups"  # directory containing MachineGroup definitions
EXEC_DIR = "exec"  # directory containing executables or their configs

# --- Static ---
STATIC_DIR = "static"  # directory containing static files served to clients

# --- iPXE ---
# File names for different actions
# These need to be configured in the data directory
IPXE_DIR = "ipxe"
# endpoint first hit by machines, configured in dhcp
IPXE_BOOT = "boot.ipxe.j2"
# second endpoint hit to chain to appropriate endpoint
IPXE_START = "start.ipxe.j2"
IPXE_PROVISION = "provision.ipxe"  # endpoint hit when provisioned
IPXE_PASSTHROUGH = "pass.ipxe"  # endpoint hit when not provisioning

# --- BUTANE ---
BUTANE_VERSION = "v0.13.1"
BUTANE_EXEC = "butane"  # relative to EXEC_DIR
BUTANE_DIR = "butane"

# --- IGNITION ---
IGNITION_DIR_PATH = "ignition"

# --- GUNICORN ---
GUNICORN_DEFAULT_CONFIG = "gunicorn_conf_default.py"
GUNICORN_CONFIG = "gunicorn_conf.py"

# --- FSDATA ---
CACHE_POLLING_INTERVAL = 1
