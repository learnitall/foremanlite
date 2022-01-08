#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=all
"""
Default configuration of gunicorn for foremanlite.

Note that in all gunicorn configuration files, current application
ServeContext instance will be made available under the 'ctx' global
variable. To access, use:

```python
globals().get('ctx')
```

For more information, see foremanlite.serve.context and
foremanlite.serve.app
"""
from foremanlite.serve.context import ServeContext

# --- Preflight check for needed context variable
_ctx: ServeContext = globals().get("ctx", None)
if _ctx is None:
    raise ValueError("Unable to get current application context.")

bind = "127.0.0.1:8080"
workers = 1
