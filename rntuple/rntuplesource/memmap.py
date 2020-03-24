"""Memmap source for RNTuple reader
Memmap source for RNTuple reader: purpose is to create a memory-map to an RNTuple stored in a binary file on disk.

Borrowed from uproot.git
# BSD 3-Clause License; see https://github.com/scikit-hep/uproot/blob/master/LICENSE
"""

from __future__ import absolute_import, print_function

import numpy

import os

import rntuple.rntuplesource.source


class MemmapSource(rntuple.rntuplesource.source.Source):
    # makes __doc__ attribute mutable before Python 3.3
    __metaclass__ = type.__new__(type, "type", (rntuple.rntuplesource.source.Source.__metaclass__,), {})

    defaults = {}

    def __init__(self, path):
        self.path = os.path.expanduser(path)
        self._source = numpy.memmap(self.path, dtype=numpy.uint8, mode="r")
        self.closed = False

    @property
    def source(self):
        if self.closed:
            raise IOError("The file handler has already been closed.")
        return self._source

    def parent(self):
        return self

    def size(self):
        return len(self.source)

    def threadlocal(self):
        return self

    def dismiss(self):
        pass

    def close(self):
        self.source._mmap.close()
        self.closed = True

    def data(self, start, stop, dtype=None):
        # assert start >= 0
        # assert stop >= 0
        # assert stop >= start

        if stop > len(self.source):
            raise IndexError("indexes {0}:{1} are beyond the end of data source {2}".format(len(self.source), stop, repr(self.path)))

        if dtype is None:
            return self.source[start:stop]
        else:
            return self.source[start:stop].view(dtype)
