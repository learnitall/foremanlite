#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Share flask resources for other Resources, Namespaces, etc."""
import typing as t
import flask


app: t.Union[None, flask.Flask] 

flask.current_app