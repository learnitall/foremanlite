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

_ctx: ServeContext = globals().get("ctx", None)
if _ctx is None:
    raise ValueError("Unable to get current application context.")

bind = "0.0.0.0:80"
workers = 1
accesslog = f"{_ctx.log_dir}/gunicorn.access.log"
errorlog = f"{_ctx.log_dir}/gunicorn.error.log"
