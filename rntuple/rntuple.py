"""
Borrowed from uproot.git
# BSD 3-Clause License; see https://github.com/scikit-hep/uproot/blob/master/LICENSE
"""

from __future__ import absolute_import, print_function

import os
import sys

from rntuple.rntuplesource.memmap import MemmapSource

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


def _bytesid(x):
    """ 
    
    Check if we are using python2 or python3 and depending on the python version
    check if objecy is strind or unicode.
      
    """
    if sys.version_info[0] > 2:
        if isinstance(x, str):
            return x.encode("ascii", "backslashreplace")
        else:
            return x
    else:
        if isinstance(x, unicode):
            return x.encode("ascii", "backslashreplace")
        else:
            return x


def open(path, localsource=MemmapSource.defaults, **options):
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
    
    if _bytesid(parsed.scheme) == b"file" or len(parsed.scheme) == 0 or (os.name == "nt" and open._windows_absolute.match(path) is not None):
        if not (os.name == "nt" and open._windows_absolute.match(path) is not None):
            path = parsed.netloc + parsed.path
        if isinstance(localsource, dict):
            kwargs = dict(MemmapSource.defaults)
            kwargs.update(localsource)
            for n in kwargs:
                if n in options:
                    kwargs[n] = options.pop(n)
            openfcn = lambda path: MemmapSource(path, **kwargs)
        else:
            openfcn = localsource
        return True
        #return ROOTDirectory.read(openfcn(path), **options)

    else:
        raise ValueError("URI scheme not recognized: {0}".format(path))
