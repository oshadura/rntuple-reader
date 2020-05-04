#!/usr/bin/env python

# BSD 3-Clause License; see https://github.com/scikit-hep/uproot/blob/master/LICENSE

"""rntuple-reader -- RNTuple I/O in pure Python and Numpy.

Basic cheat-sheet
-----------------


"""

from __future__ import absolute_import

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

# high-level entry points
from rntuple.rntuple import open

# convenient access to the version number
from rntuple.version import __version__

__all__ = ["open", "__version__"]
