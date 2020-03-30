#!/usr/bin/env python

# BSD 3-Clause License; see https://github.com/scikit-hep/uproot/blob/master/LICENSE

"""rntuple-reader -- RNTuple I/O in pure Python and Numpy.

Basic cheat-sheet
-----------------


"""

from __future__ import absolute_import

# high-level entry points
from rntuple.rntuple import open
from rntuple.rntuplesource.memmap import MemmapSource

# convenient access to the version number
from rntuple.version import __version__

__all__ = ["open", "__version__"]
