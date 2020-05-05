"""
"""

from __future__ import absolute_import, print_function

import os
import re
import struct
import sys

import numpy

import uproot
import uproot_methods

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

def open(path, localsource=uproot.MemmapSource.defaults, **options):
    """ Function that open RNTuple file (.root extension)
    
    Parameters:
    path (string): 
    localsource (string):
    
    Returns:
    """
    if isinstance(path, getattr(os, "PathLike", ())):
        path = os.fspath(path)
    elif hasattr(path, "__fspath__"):
        path = path.__fspath__()
    elif path.__class__.__module__ == "pathlib":
        import pathlib
        if isinstance(path, pathlib.Path):
            path = str(path)

    parsed = urlparse(path)
    
    if uproot.rootio._bytesid(parsed.scheme) == b"file" or len(parsed.scheme) == 0 or (os.name == "nt" and open._windows_absolute.match(path) is not None):
        if not (os.name == "nt" and open._windows_absolute.match(path) is not None):
            path = parsed.netloc + parsed.path
        if isinstance(localsource, dict):
            kwargs = dict(uproot.MemmapSource.defaults)
            kwargs.update(localsource)
            for n in kwargs:
                if n in options:
                    kwargs[n] = options.pop(n)
            openfcn = lambda path:uproot.MemmapSource(path, **kwargs)
        else:
            openfcn = localsource
        return uproot.rootio.ROOTDirectory.read(openfcn(path), **options)

    else:
        raise ValueError("URI scheme not recognized: {0}".format(path))
