#!/usr/bin/env python

from __future__ import absolute_import

import re

__version__ = "0.0.1"
version = __version__
version_info = tuple(re.split(r"[-\.]", __version__))

del re