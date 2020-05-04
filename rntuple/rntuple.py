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


class ROOT_3a3a_Experimental_3a3a_RNTuple(uproot.rootio.ROOTStreamedObject):
    _classname = b"ROOT::Experimental::RNTuple"
    classname = "ROOT::Experimental::RNTuple"
    _fields = ["fVersion",
               "fSize",
               "fSeekHeader",
               "fNBytesHeader",
               "fLenHeader",
               "fSeekFooter",
               "fNBytesFooter",
               "fLenFooter",
               "fReserved"]

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = uproot._startcheck(source, cursor)
        cursor.skip(4)
        self._fVersion, self._fSize, self._fSeekHeader, self._fNBytesHeader, self._fLenHeader, self._fSeekFooter, self._fNBytesFooter, self._fLenFooter, self._fReserved = cursor.fields(source, ROOT_3a3a_Experimental_3a3a_RNTuple._format1)
        return self

    _format1 = struct.Struct(">IIQIIQIIQ")

class Undefined(uproot.rootio.ROOTStreamedObject):
    _classname = None
    classname = None

    @classmethod
    def read(cls, source, cursor, context, parent, classname=None):
        if cls._copycontext:
            context = context.copy()
        out = cls.__new__(cls)
        out = cls._readinto(out, source, cursor, context, parent)
        out._postprocess(source, cursor, context, parent)
        out._classname = classname
        return out

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        self._cursor = cursor.copied()
        start, cnt, self._classversion = uproot._startcheck(source, cursor)
        if cnt is None:
            raise TypeError("cannot read objects of type {0} and cannot even skip over this one (returning Undefined) because its size is not known\n  in file: {1}".format("???" if self._classname is None else self._classname.decode("ascii"), context.sourcepath))

        cursor.skip(cnt - 6)
        uproot._endcheck(start, cursor, cnt)
        return self

    def __repr__(self):
        if self._classname is not None:
            return "<{0} (failed to read {1} version {2}) at 0x{3:012x}>".format(self.__class__.__name__, repr(self._classname), self._classversion, id(self))
        else:
            return "<{0} at 0x{1:012x}>".format(self.__class__.__name__, id(self))

builtin_classes = {"uproot_methods": uproot.rootio.uproot_methods,
                   "TObject":        uproot.rootio.TObject,
                   "TString":        uproot.rootio.TString,
                   "TNamed":         uproot.rootio.TNamed,
                   "TObjArray":      uproot.rootio.TObjArray,
                   "TObjString":     uproot.rootio.TObjString,
                   "TList":          uproot.rootio.TList,
                   "THashList":      uproot.rootio.THashList,
                   "TRef":           uproot.rootio.TRef,
                   "TArray":         uproot.rootio.TArray,
                   "TArrayC":        uproot.rootio.TArrayC,
                   "TArrayS":        uproot.rootio.TArrayS,
                   "TArrayI":        uproot.rootio.TArrayI,
                   "TArrayL":        uproot.rootio.TArrayL,
                   "TArrayL64":      uproot.rootio.TArrayL64,
                   "TArrayF":        uproot.rootio.TArrayF,
                   "TArrayD":        uproot.rootio.TArrayD,
                   "TRefArray":      uproot.rootio.TRefArray,
                   "ROOT_3a3a_TIOFeatures": uproot.rootio.ROOT_3a3a_TIOFeatures,
                   "ROOT_3a3a_Experimental_3a3a_RNTuple": ROOT_3a3a_Experimental_3a3a_RNTuple}

builtin_skip =    {"TBranch":    ["fBaskets"],
                   "TTree":      ["fUserInfo", "fBranchRef"]}
