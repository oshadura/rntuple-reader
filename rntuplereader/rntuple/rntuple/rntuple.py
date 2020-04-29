"""
"""

from __future__ import absolute_import, print_function

import os
import sys
import re

from uproot import struct

from rntuple.backend.memmap_backend import MemmapBackend

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


def open(path, localsource=MemmapBackend.defaults, **options):
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
            kwargs = dict(MemmapBackend.defaults)
            kwargs.update(localsource)
            for n in kwargs:
                if n in options:
                    kwargs[n] = options.pop(n)
            openfcn = lambda path:MemmapBackend(path, **kwargs)
        else:
            openfcn = localsource
        #return ROOTMiniFile.read(openfcn(path), **options)
        return ROOTDirectory.read(openfcn(path), **options)

    else:
        raise ValueError("URI scheme not recognized: {0}".format(path))

open._windows_absolute = re.compile(r"^[A-Za-z]:\\")

def nofilter(x): return True

################################################################ ROOTDirectory

class ROOTDirectory(object):
    # makes __doc__ attribute mutable before Python 3.3
    __metaclass__ = type.__new__(type, "type", (type,), {})

    _classname = b"TDirectory"
    classname = "TDirectory"

    class _FileContext(object):
        def __init__(self, sourcepath, streamerinfos, streamerinfosmap, classes, compression, tfile):
            self.sourcepath, self.streamerinfos, self.streamerinfosmap, self.classes, self.compression, self.tfile = sourcepath, streamerinfos, streamerinfosmap, classes, compression, tfile
            self.uuid = tfile["_fUUID"]

        def copy(self):
            out = ROOTDirectory._FileContext.__new__(ROOTDirectory._FileContext)
            out.__dict__.update(self.__dict__)
            return out

    @staticmethod
    def read(source, *args, **options):
        if len(args) == 0:
            try:
                read_streamers = options.pop("read_streamers", True)
                if len(options) > 0:
                    raise TypeError("unrecognized options: {0}".format(", ".join(options)))

                # See https://root.cern/doc/master/classTFile.html
                cursor = Cursor(0)
                magic, fVersion = cursor.fields(source, ROOTDirectory._format1)
                if magic != b"root":
                    raise ValueError("not a ROOT file (starts with {0} instead of 'root')\n   in file: {1}".format(repr(magic), source.path))
                if fVersion < 1000000:
                    fBEGIN, fEND, fSeekFree, fNbytesFree, nfree, fNbytesName, fUnits, fCompress, fSeekInfo, fNbytesInfo, fUUID = cursor.fields(source, ROOTDirectory._format2_small)
                else:
                    fBEGIN, fEND, fSeekFree, fNbytesFree, nfree, fNbytesName, fUnits, fCompress, fSeekInfo, fNbytesInfo, fUUID = cursor.fields(source, ROOTDirectory._format2_big)

                tfile = {"_fVersion": fVersion, "_fBEGIN": fBEGIN, "_fEND": fEND, "_fSeekFree": fSeekFree, "_fNbytesFree": fNbytesFree, "nfree": nfree, "_fNbytesName": fNbytesName, "_fUnits": fUnits, "_fCompress": fCompress, "_fSeekInfo": fSeekInfo, "_fNbytesInfo": fNbytesInfo, "_fUUID": fUUID}

                # classes requried to read streamers (bootstrap)
                streamerclasses = {"TStreamerInfo":             TStreamerInfo,
                                   "TStreamerElement":          TStreamerElement,
                                   "TStreamerBase":             TStreamerBase,
                                   "TStreamerBasicType":        TStreamerBasicType,
                                   "TStreamerBasicPointer":     TStreamerBasicPointer,
                                   "TStreamerLoop":             TStreamerLoop,
                                   "TStreamerObject":           TStreamerObject,
                                   "TStreamerObjectPointer":    TStreamerObjectPointer,
                                   "TStreamerObjectAny":        TStreamerObjectAny,
                                   "TStreamerObjectAnyPointer": TStreamerObjectAnyPointer,
                                   "TStreamerString":           TStreamerString,
                                   "TStreamerSTL":              TStreamerSTL,
                                   "TStreamerSTLstring":        TStreamerSTLstring,
                                   "TStreamerArtificial":       TStreamerArtificial,
                                   "TList":                     TList,
                                   "TObjArray":                 TObjArray,
                                   "TObjString":                TObjString}

                if read_streamers and fSeekInfo != 0:
                    streamercontext = ROOTDirectory._FileContext(source.path, None, None, streamerclasses, uproot.source.compressed.Compression(fCompress), tfile)
                    streamerkey = TKey.read(source, Cursor(fSeekInfo), streamercontext, None)
                    streamerinfos, streamerinfosmap, streamerrules = _readstreamers(streamerkey._source, streamerkey._cursor, streamercontext, None)
                else:
                    streamerinfos, streamerinfosmap, streamerrules = [], {}, []

                classes = dict(globals())
                classes.update(builtin_classes)
                classes = _defineclasses(streamerinfos, classes)
                context = ROOTDirectory._FileContext(source.path, streamerinfos, streamerinfosmap, classes, uproot.source.compressed.Compression(fCompress), tfile)
                context.source = source

                keycursor = Cursor(fBEGIN)
                mykey = TKey.read(source, keycursor, context, None)

                return ROOTDirectory.read(source, Cursor(fBEGIN + fNbytesName), context, mykey)

            except Exception:
                source.dismiss()
                raise

        else:
            try:
                if len(options) > 0:
                    raise TypeError("unrecognized options: {0}".format(", ".join(options)))

                cursor, context, mykey = args

                # See https://root.cern/doc/master/classTDirectoryFile.html.
                fVersion, fDatimeC, fDatimeM, fNbytesKeys, fNbytesName = cursor.fields(source, ROOTDirectory._format3)
                if fVersion <= 1000:
                    fSeekDir, fSeekParent, fSeekKeys = cursor.fields(source, ROOTDirectory._format4_small)
                else:
                    fSeekDir, fSeekParent, fSeekKeys = cursor.fields(source, ROOTDirectory._format4_big)

                if fSeekKeys == 0:
                    out = ROOTDirectory(b"(empty)", context, [])

                else:
                    subcursor = Cursor(fSeekKeys)
                    headerkey = TKey.read(source, subcursor, context, None)

                    nkeys = subcursor.field(source, ROOTDirectory._format5)
                    keys = [TKey.read(source, subcursor, context, None) for i in range(nkeys)]

                    out = ROOTDirectory(mykey._fName, context, keys)

                out._fVersion, out._fDatimeC, out._fDatimeM, out._fNbytesKeys, out._fNbytesName, out._fSeekDir, out._fSeekParent, out._fSeekKeys = fVersion, fDatimeC, fDatimeM, fNbytesKeys, fNbytesName, fSeekDir, fSeekParent, fSeekKeys
                out.source = source
                return out

            finally:
                source.dismiss()

    _format1       = struct.Struct(">4si")
    _format2_small = struct.Struct(">iiiiiiBiii18s")
    _format2_big   = struct.Struct(">iqqiiiBiqi18s")
    _format3       = struct.Struct(">hIIii")
    _format4_small = struct.Struct(">iii")
    _format4_big   = struct.Struct(">qqq")
    _format5       = struct.Struct(">i")

    def __init__(self, name, context, keys):
        self.name, self._context, self._keys = name, context, keys

    @property
    def compression(self):
        return self._context.compression

    def __repr__(self):
        return "<ROOTDirectory {0} at 0x{1:012x}>".format(repr(self.name), id(self))

    def __getitem__(self, name):
        return self.get(name)

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return self.iterkeys()

    @staticmethod
    def _withoutcycle(key):
        return "{0}".format(key._fName.decode("ascii")).encode("ascii")

    @staticmethod
    def _withcycle(key):
        return "{0};{1}".format(key._fName.decode("ascii"), key._fCycle).encode("ascii")

    def showstreamers(self, filtername=nofilter, stream=sys.stdout):
        if stream is None:
            return "\n".join(x.show(stream=stream) for x in self._context.streamerinfos if filtername(x._fName))
        else:
            for x in self._context.streamerinfos:
                if filtername(x._fName):
                    x.show(stream=stream)

    def iterkeys(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        for key in self._keys:
            cls = _classof(self._context, key._fClassName)
            if filtername(key._fName) and filterclass(cls):
                yield self._withcycle(key)

            if recursive and (key._fClassName == b"TDirectory" or key._fClassName == b"TDirectoryFile"):
                for name in key.get().iterkeys(recursive, filtername, filterclass):
                    yield "{0}/{1}".format(self._withoutcycle(key).decode("ascii"), name.decode("ascii")).encode("ascii")

    def itervalues(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        for key in self._keys:
            cls = _classof(self._context, key._fClassName)
            if filtername(key._fName) and filterclass(cls):
                yield key.get()

            if recursive and (key._fClassName == b"TDirectory" or key._fClassName == b"TDirectoryFile"):
                for value in key.get().itervalues(recursive, filtername, filterclass):
                    yield value

    def iteritems(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        for key in self._keys:
            cls = _classof(self._context, key._fClassName)
            if filtername(key._fName) and filterclass(cls):
                yield self._withcycle(key), key.get()

            if recursive and (key._fClassName == b"TDirectory" or key._fClassName == b"TDirectoryFile"):
                for name, value in key.get().iteritems(recursive, filtername, filterclass):
                    yield "{0}/{1}".format(self._withoutcycle(key).decode("ascii"), name.decode("ascii")).encode("ascii"), value

    def iterclasses(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        for key in self._keys:
            cls = _classof(self._context, key._fClassName)
            if filtername(key._fName) and filterclass(cls):
                yield self._withcycle(key), cls

            if recursive and (key._fClassName == b"TDirectory" or key._fClassName == b"TDirectoryFile"):
                for name, classname in key.get().iterclasses(recursive, filtername, filterclass):
                    yield "{0}/{1}".format(self._withoutcycle(key).decode("ascii"), name.decode("ascii")).encode("ascii"), classname

    def iterclassnames(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        for key in self._keys:
            cls = _classof(self._context, key._fClassName)
            if filtername(key._fName) and filterclass(cls):
                yield self._withcycle(key), key._fClassName.decode('ascii')

            if recursive and (key._fClassName == b"TDirectory" or key._fClassName == b"TDirectoryFile"):
                for name, classname in key.get().iterclassnames(recursive, filtername, filterclass):
                    yield "{0}/{1}".format(self._withoutcycle(key).decode("ascii"), name.decode("ascii")).encode("ascii"), classname

    def keys(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return list(self.iterkeys(recursive=recursive, filtername=filtername, filterclass=filterclass))

    def _ipython_key_completions_(self):
        "Support for completion of keys in an IPython kernel"
        return [item.decode("ascii") for item in self.iterkeys()]

    def values(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return list(self.itervalues(recursive=recursive, filtername=filtername, filterclass=filterclass))

    def items(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return list(self.iteritems(recursive=recursive, filtername=filtername, filterclass=filterclass))

    def classes(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return list(self.iterclasses(recursive=recursive, filtername=filtername, filterclass=filterclass))

    def classnames(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return list(self.iterclassnames(recursive=recursive, filtername=filtername, filterclass=filterclass))

    def allkeys(self, filtername=nofilter, filterclass=nofilter):
        return self.keys(recursive=True, filtername=filtername, filterclass=filterclass)

    def allvalues(self, filtername=nofilter, filterclass=nofilter):
        return self.values(recursive=True, filtername=filtername, filterclass=filterclass)

    def allitems(self, filtername=nofilter, filterclass=nofilter):
        return self.items(recursive=True, filtername=filtername, filterclass=filterclass)

    def allclasses(self, filtername=nofilter, filterclass=nofilter):
        return self.classes(recursive=True, filtername=filtername, filterclass=filterclass)

    def allclassnames(self, filtername=nofilter, filterclass=nofilter):
        return self.classnames(recursive=True, filtername=filtername, filterclass=filterclass)

    def get(self, name, cycle=None):
        name = _bytesid(name)

        if b"/" in name:
            out = self
            for n in name.split(b"/"):
                out = out.get(n, cycle)
            return out

        else:
            if cycle is None and b";" in name:
                at = name.rindex(b";")
                name, cycle = name[:at], name[at + 1:]
                cycle = int(cycle)

            last = None
            for key in self._keys:
                if key._fName == name:
                    if cycle == key._fCycle:
                        return key.get()
                    elif cycle is None and last is None:
                        last = key
                    elif cycle is None and last._fCycle < key._fCycle:
                        last = key

            if last is not None:
                return last.get()
            elif cycle is None:
                raise _KeyError("not found: {0}\n in file: {1}".format(repr(name), self._context.sourcepath))
            else:
                raise _KeyError("not found: {0} with cycle {1}\n in file: {2}".format(repr(name), cycle, self._context.sourcepath))

    def close(self):
        self._context.source.close()

    def __contains__(self, name):
        try:
            self.get(name)
        except KeyError:
            return False
        else:
            return True

    def __enter__(self, *args, **kwds):
        return self

    def __exit__(self, *args, **kwds):
        self.close()

class _KeyError(KeyError):
    def __str__(self):
        return self.args[0]

_KeyError.__name__ = "KeyError"
_KeyError.__module__ = "builtins" if sys.version_info[0] > 2 else None

################################################################ helper functions for common tasks

def _memsize(data):
    if isinstance(data, str):
        m = re.match(r"^\s*([+-]?(\d+(\.\d*)?|\.\d+)(e[+-]?\d+)?)\s*([kmgtpezy]?b)\s*$", data, re.I)
        if m is not None:
            target, unit = float(m.group(1)), m.group(5).upper()
            if unit == "KB":
                target *= 1024
            elif unit == "MB":
                target *= 1024**2
            elif unit == "GB":
                target *= 1024**3
            elif unit == "TB":
                target *= 1024**4
            elif unit == "PB":
                target *= 1024**5
            elif unit == "EB":
                target *= 1024**6
            elif unit == "ZB":
                target *= 1024**7
            elif unit == "YB":
                target *= 1024**8
            return target
    return None

def _bytesid(x):
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

def _startcheck(source, cursor):
    start = cursor.index
    cnt, vers = cursor.fields(source, _startcheck._format_cntvers)
    if numpy.int64(cnt) & uproot.const.kByteCountMask:
        cnt = int(numpy.int64(cnt) & ~uproot.const.kByteCountMask)
        return start, cnt + 4, vers
    else:
        cursor.index = start
        vers, = cursor.fields(source, _startcheck._format_cntvers2)
        return start, None, vers
_startcheck._format_cntvers = struct.Struct(">IH")
_startcheck._format_cntvers2 = struct.Struct(">H")

def _endcheck(start, cursor, cnt):
    if cnt is not None:
        observed = cursor.index - start
        if observed != cnt:
            raise ValueError("object has {0} bytes; expected {1}".format(observed, cnt))

def _skiptobj(source, cursor):
    version = cursor.field(source, _skiptobj._format1)
    if numpy.int64(version) & uproot.const.kByteCountVMask:
        cursor.skip(4)
    fUniqueID, fBits = cursor.fields(source, _skiptobj._format2)
    fBits = numpy.uint32(fBits) | uproot.const.kIsOnHeap
    if fBits & uproot.const.kIsReferenced:
        cursor.skip(2)
_skiptobj._format1 = struct.Struct(">h")
_skiptobj._format2 = struct.Struct(">II")

def _nametitle(source, cursor):
    start, cnt, vers = _startcheck(source, cursor)
    _skiptobj(source, cursor)
    name = cursor.string(source)
    title = cursor.string(source)
    _endcheck(start, cursor, cnt)
    return name, title

def _mapstrstr(source, cursor):
    cursor.skip(12)
    size = cursor.field(source, _mapstrstr._int32)
    cursor.skip(6)
    keys = [cursor.string(source) for i in range(size)]
    cursor.skip(6)
    values = [cursor.string(source) for i in range(size)]
    return dict(zip(keys, values))

_mapstrstr._int32 = struct.Struct('>I')

def _readobjany(source, cursor, context, parent, asclass=None):
    # TBufferFile::ReadObjectAny()
    # https://github.com/root-project/root/blob/c4aa801d24d0b1eeb6c1623fd18160ef2397ee54/io/io/src/TBufferFile.cxx#L2684
    # https://github.com/root-project/root/blob/c4aa801d24d0b1eeb6c1623fd18160ef2397ee54/io/io/src/TBufferFile.cxx#L2404

    beg = cursor.index - cursor.origin
    bcnt = cursor.field(source, struct.Struct(">I"))

    if numpy.int64(bcnt) & uproot.const.kByteCountMask == 0 or numpy.int64(bcnt) == uproot.const.kNewClassTag:
        vers = 0
        start = 0
        tag = bcnt
        bcnt = 0
    else:
        vers = 1
        start = cursor.index - cursor.origin
        tag = cursor.field(source, struct.Struct(">I"))

    if numpy.int64(tag) & uproot.const.kClassMask == 0:
        # reference object
        if tag == 0:
            return None                                         # return null

        elif tag == 1:
            return parent

        elif tag not in cursor.refs:
            # jump past this object
            cursor.index = cursor.origin + beg + bcnt + 4
            return None                                         # return null

        else:
            return cursor.refs[tag]                             # return object

    elif tag == uproot.const.kNewClassTag:
        # new class and object
        cname = cursor.cstring(source).decode("ascii")

        fct = context.classes.get(cname, Undefined)

        if vers > 0:
            cursor.refs[start + uproot.const.kMapOffset] = fct
        else:
            cursor.refs[len(cursor.refs) + 1] = fct

        if asclass is None:
            obj = fct.read(source, cursor, context, parent)     # new object
            if isinstance(obj, Undefined):
                obj._classname = cname
        else:
            obj = asclass.read(source, cursor, context, parent) # placeholder new object

        if vers > 0:
            cursor.refs[beg + uproot.const.kMapOffset] = obj
        else:
            cursor.refs[len(cursor.refs) + 1] = obj

        return obj                                              # return object

    else:
        # reference class, new object
        ref = int(numpy.int64(tag) & ~uproot.const.kClassMask)

        if asclass is None:
            if ref not in cursor.refs:
                raise IOError("invalid class-tag reference\nin file: {0}".format(context.sourcepath))

            fct = cursor.refs[ref]                              # reference class

            if fct not in context.classes.values():
                raise IOError("invalid class-tag reference (not a recognized class: {0})\nin file: {1}".format(fct, context.sourcepath))

            obj = fct.read(source, cursor, context, parent)     # new object

        else:
            obj = asclass.read(source, cursor, context, parent) # placeholder new object

        if vers > 0:
            cursor.refs[beg + uproot.const.kMapOffset] = obj
        else:
            cursor.refs[len(cursor.refs) + 1] = obj

        return obj                                              # return object

def _classof(context, classname):
    if classname == b"TDirectory" or classname == b"TDirectoryFile":
        cls = ROOTDirectory
    else:
        cls = context.classes.get(_safename(classname), None)
        if cls is None:
            cls = ROOTObject.__metaclass__("Undefined_" + str(_safename(classname)), (Undefined,), {"_classname": classname})
    return cls

def _readstreamers(source, cursor, context, parent):
    tlist = TList.read(source, cursor, context, parent)

    streamerinfos = []
    streamerrules = []
    for obj in tlist:
        if isinstance(obj, TStreamerInfo):
            dependencies = set()
            for element in obj._fElements:
                if isinstance(element, TStreamerBase):
                    dependencies.add(element._fName)
                # if isinstance(element, (TStreamerObject, TStreamerObjectAny, TStreamerString)) or (isinstance(element, TStreamerObjectPointer) and element._fType == uproot.const.kObjectp):
                #     dependencies.add(element._fTypeName.rstrip(b"*"))
            streamerinfos.append((obj, dependencies))

        elif isinstance(obj, TList) and all(isinstance(x, TObjString) for x in obj):
            streamerrules.append(obj)

        else:
            raise ValueError("expected TStreamerInfo or TList of TObjString in streamer info array\n   in file: {0}".format(context.sourcepath))

    # https://stackoverflow.com/a/11564769/1623645
    def topological_sort(items):
        provided = set([x.encode("ascii") for x in builtin_classes])
        while len(items) > 0:
            remaining_items = []
            emitted = False

            for item, dependencies in items:
                if dependencies.issubset(provided):
                    yield item
                    provided.add(item._fName)
                    emitted = True
                else:
                    remaining_items.append((item, dependencies))

            if not emitted:
                for pair in items:
                    if pair in remaining_items:
                        remaining_items.remove(pair)
                # raise ValueError("cannot sort TStreamerInfos into dependency order:\n\n{0}".format("\n".join("{0:20s} requires {1}".format(item._fName.decode("ascii"), " ".join(x.decode("ascii") for x in dependencies)) for item, dependencies in items)))

            items = remaining_items

    streamerinfos = list(topological_sort(streamerinfos))
    streamerinfosmap = dict((x._fName, x) for x in streamerinfos)

    for streamerinfo in streamerinfos:
        streamerinfo.members = {}
        for element in streamerinfo._fElements:
            if isinstance(element, TStreamerBase):
                if element._fName in streamerinfosmap:
                    streamerinfo.members.update(getattr(streamerinfosmap[element._fName], "members", {}))
            else:
                streamerinfo.members[element._fName] = element

    return streamerinfos, streamerinfosmap, streamerrules

def _ftype2dtype(fType):
    if fType == uproot.const.kBool:
        return "numpy.dtype(numpy.bool_)"
    elif fType == uproot.const.kChar:
        return "numpy.dtype('i1')"
    elif fType in (uproot.const.kUChar, uproot.const.kCharStar):
        return "numpy.dtype('u1')"
    elif fType == uproot.const.kShort:
        return "numpy.dtype('>i2')"
    elif fType == uproot.const.kUShort:
        return "numpy.dtype('>u2')"
    elif fType == uproot.const.kInt:
        return "numpy.dtype('>i4')"
    elif fType in (uproot.const.kBits, uproot.const.kUInt, uproot.const.kCounter):
        return "numpy.dtype('>u4')"
    elif fType == uproot.const.kLong:
        return "numpy.dtype(numpy.long).newbyteorder('>')"
    elif fType == uproot.const.kULong:
        return "numpy.dtype('>u' + repr(numpy.dtype(numpy.long).itemsize))"
    elif fType == uproot.const.kLong64:
        return "numpy.dtype('>i8')"
    elif fType == uproot.const.kULong64:
        return "numpy.dtype('>u8')"
    elif fType in (uproot.const.kFloat, uproot.const.kFloat16):
        return "numpy.dtype('>f4')"
    elif fType in (uproot.const.kDouble, uproot.const.kDouble32):
        return "numpy.dtype('>f8')"
    else:
        return "None"

def _ftype2struct(fType):
    if fType == uproot.const.kBool:
        return "?"
    elif fType == uproot.const.kChar:
        return "b"
    elif fType in (uproot.const.kUChar, uproot.const.kCharStar):
        return "B"
    elif fType == uproot.const.kShort:
        return "h"
    elif fType == uproot.const.kUShort:
        return "H"
    elif fType == uproot.const.kInt:
        return "i"
    elif fType in (uproot.const.kBits, uproot.const.kUInt, uproot.const.kCounter):
        return "I"
    elif fType == uproot.const.kLong:
        return "l"
    elif fType == uproot.const.kULong:
        return "L"
    elif fType == uproot.const.kLong64:
        return "q"
    elif fType == uproot.const.kULong64:
        return "Q"
    elif fType in (uproot.const.kFloat, uproot.const.kFloat16):
        return "f"
    elif fType in (uproot.const.kDouble, uproot.const.kDouble32):
        return "d"
    else:
        raise NotImplementedError(fType)

def _safename(name):
    out = _safename._pattern.sub(lambda bad: "_" + "".join("{0:02x}".format(ord(x)) for x in bad.group(0)) + "_", name.decode("ascii"))
    if keyword.iskeyword(out):
        out = out + "__"
    return out
_safename._pattern = re.compile("[^a-zA-Z0-9]+")

def _raise_notimplemented(streamertype, streamerdict, source, cursor):
    raise NotImplementedError("\n\nUnimplemented streamer type: {0}\n\nmembers: {1}\n\nfile contents:\n\n{2}".format(streamertype, streamerdict, cursor.hexdump(source)))

def _resolveversion(cls, self, classversion):
    if classversion not in cls._versions:
        raise ValueError("attempting to read {0} object with version {1}, but there is no streamer in this ROOT file with that class name and version (versions available: {2})".format(cls.__name__, classversion, list(cls._versions.keys())))
    self.__class__ = cls._versions[classversion]

def _defineclasses(streamerinfos, classes):
    skip = dict(builtin_skip)

    for streamerinfo in streamerinfos:
        pyclassname = _safename(streamerinfo._fName)

        if isinstance(streamerinfo, TStreamerInfo) and pyclassname not in builtin_classes and (pyclassname not in classes or hasattr(classes[pyclassname], "_versions")):
            hasreadobjany = False

            code = ["    @classmethod",
                    "    def _readinto(cls, self, source, cursor, context, parent, asclass=None):",
                    "        start, cnt, classversion = _startcheck(source, cursor)",
                    "        startendcheck = True",
                    "        if cls._classversion != classversion:",
                    "            cursor.index = start",
                    "            if classversion in cls._versions:",
                    "                return cls._versions[classversion]._readinto(self, source, cursor, context, parent)",
                    "            elif cnt is None:",
                    "                startendcheck = False",
                    "            else:",
                    "                return Undefined.read(source, cursor, context, parent, cls.__name__)"]

            fields = []
            recarray = []
            bases = []
            formats = {}
            dtypes = {}
            basicnames = []
            basicletters = ""
            for elementi, element in enumerate(streamerinfo._fElements):
                if isinstance(element, TStreamerArtificial):
                    code.append("        _raise_notimplemented({0}, {1}, source, cursor)".format(repr(element.__class__.__name__), repr(repr(element.__dict__))))
                    recarray.append("raise ValueError('not a recarray')")

                elif isinstance(element, TStreamerBase):
                    code.append("        {0}._readinto(self, source, cursor, context, parent)".format(_safename(element._fName)))
                    bases.append(_safename(element._fName))

                elif isinstance(element, TStreamerBasicPointer):
                    assert uproot.const.kOffsetP < element._fType < uproot.const.kOffsetP + 20
                    fType = element._fType - uproot.const.kOffsetP

                    dtypename = "_dtype{0}".format(len(dtypes) + 1)
                    dtypes[dtypename] = _ftype2dtype(fType)

                    code.append("        fBasketSeek_dtype = cls.{0}".format(dtypename))
                    if streamerinfo._fName == b"TBranch" and element._fName == b"fBasketSeek":
                        code.append("        if getattr(context, \"speedbump\", True):")
                        code.append("            if cursor.bytes(source, 1)[0] == 2:")
                        code.append("                fBasketSeek_dtype = numpy.dtype('>i8')")
                    else:
                        code.append("        if getattr(context, \"speedbump\", True):")
                        code.append("            cursor.skip(1)")

                    code.append("        self._{0} = cursor.array(source, self._{1}, fBasketSeek_dtype)".format(_safename(element._fName), _safename(element._fCountName)))
                    fields.append(_safename(element._fName))
                    recarray.append("raise ValueError('not a recarray')")

                elif isinstance(element, TStreamerBasicType):
                    if element._fArrayLength == 0:
                        basicnames.append("self._{0}".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                        fielddtype = _ftype2dtype(element._fType)
                        if fielddtype == "None":
                            recarray.append("raise ValueError('not a recarray')")
                        else:
                            recarray.append("out.append(({0}, {1}))".format(repr(str(element._fName.decode("ascii"))), fielddtype))
                        basicletters += _ftype2struct(element._fType)

                        if elementi + 1 == len(streamerinfo._fElements) or not isinstance(streamerinfo._fElements[elementi + 1], TStreamerBasicType) or streamerinfo._fElements[elementi + 1]._fArrayLength != 0:
                            formatnum = len(formats) + 1
                            formats["_format{0}".format(formatnum)] = "struct.Struct('>{0}')".format(basicletters)

                            if len(basicnames) == 1:
                                code.append("        {0} = cursor.field(source, cls._format{1})".format(basicnames[0], formatnum))
                            else:
                                code.append("        {0} = cursor.fields(source, cls._format{1})".format(", ".join(basicnames), formatnum))

                            basicnames = []
                            basicletters = ""

                    else:
                        dtypename = "_dtype{0}".format(len(dtypes) + 1)
                        fielddtype = dtypes[dtypename] = _ftype2dtype(element._fType)
                        code.append("        self._{0} = cursor.array(source, {1}, cls.{2})".format(_safename(element._fName), element._fArrayLength, dtypename))
                        fields.append(_safename(element._fName))
                        if fielddtype == "None":
                            recarray.append("raise ValueError('not a recarray')")
                        else:
                            recarray.append("out.append(({0}, {1}, {2}))".format(repr(str(element._fName.decode("ascii"))), fielddtype, element._fArrayLength))

                elif isinstance(element, TStreamerLoop):
                    code.extend(["        cursor.skip(6)",
                                 "        for index in range(self._{0}):".format(_safename(element._fCountName)),
                                 "            self._{0} = {1}.read(source, cursor, context, self)".format(_safename(element._fName), _safename(element._fTypeName.rstrip(b"*")))])

                elif isinstance(element, (TStreamerObjectAnyPointer, TStreamerObjectPointer)):
                    if element._fType == uproot.const.kObjectp or element._fType == uproot.const.kAnyp:
                        if pyclassname in skip and _safename(element._fName) in skip[pyclassname]:
                            code.append("        Undefined.read(source, cursor, context, self)")
                        else:
                            code.append("        self._{0} = {1}.read(source, cursor, context, self)".format(_safename(element._fName), _safename(element._fTypeName.rstrip(b"*"))))
                            fields.append(_safename(element._fName))
                            recarray.append("out.extend({0}._recarray())".format(_safename(element._fName)))
                    elif element._fType == uproot.const.kObjectP or element._fType == uproot.const.kAnyP:
                        if pyclassname in skip and _safename(element._fName) in skip[pyclassname]:
                            code.append("        _readobjany(source, cursor, context, parent, asclass=Undefined)")
                            hasreadobjany = True
                        else:
                            code.append("        self._{0} = _readobjany(source, cursor, context, parent)".format(_safename(element._fName)))
                            hasreadobjany = True
                            fields.append(_safename(element._fName))
                            recarray.append("raise ValueError('not a recarray')")
                    else:
                        code.append("        _raise_notimplemented({0}, {1}, source, cursor)".format(repr(element.__class__.__name__), repr(repr(element.__dict__))))
                        recarray.append("raise ValueError('not a recarray')")

                elif isinstance(element, TStreamerSTL):
                    if element._fSTLtype == uproot.const.kSTLstring or element._fTypeName == b"string":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.string(source)".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kBool) or element._fTypeName == b"vector<bool>" or element._fTypeName == b"vector<Bool_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), '?')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kChar) or element._fTypeName == b"vector<char>" or element._fTypeName == b"vector<Char_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), 'i1')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kUChar) or element._fTypeName == b"vector<unsigned char>" or element._fTypeName == b"vector<UChar_t>" or element._fTypeName == b"vector<Byte_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), 'u1')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kShort) or element._fTypeName == b"vector<short>" or element._fTypeName == b"vector<Short_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), '>i2')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kUShort) or element._fTypeName == b"vector<unsigned short>" or element._fTypeName == b"vector<UShort_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), '>u2')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kInt) or element._fTypeName == b"vector<int>" or element._fTypeName == b"vector<Int_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), '>i4')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kUInt) or element._fTypeName == b"vector<unsigned int>" or element._fTypeName == b"vector<UInt_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), '>u4')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kLong) or element._fTypeName == b"vector<long>" or element._fTypeName == b"vector<Long_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), '>i8')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kULong) or element._fTypeName == b"vector<unsigned long>" or element._fTypeName == b"vector<ULong64_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), '>u8')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kFloat) or element._fTypeName == b"vector<float>" or element._fTypeName == b"vector<Float_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), '>f4')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif (element._fSTLtype == uproot.const.kSTLvector and element._fCtype == uproot.const.kDouble) or element._fTypeName == b"vector<double>" or element._fTypeName == b"vector<Double_t>":
                        code.append("        cursor.skip(6)")
                        code.append("        self._{0} = cursor.array(source, cursor.field(source, self._int32), '>f8')".format(_safename(element._fName)))
                        fields.append(_safename(element._fName))
                    elif element._fTypeName == b"map<string,string>":
                        code.append("        self._{0} = _mapstrstr(source, cursor)".format(_safename(element._fName)))
                    else:
                        code.append("        _raise_notimplemented({0}, {1}, source, cursor)".format(repr(element.__class__.__name__), repr(repr(element.__dict__))))
                    recarray.append("raise ValueError('not a recarray')")

                elif isinstance(element, TStreamerSTLstring):
                    code.append("        _raise_notimplemented({0}, {1}, source, cursor)".format(repr(element.__class__.__name__), repr(repr(element.__dict__))))
                    recarray.append("raise ValueError('not a recarray')")

                elif isinstance(element, (TStreamerObject, TStreamerObjectAny, TStreamerString)):
                    if pyclassname in skip and _safename(element._fName) in skip[pyclassname]:
                        code.append("        self._{0} = Undefined.read(source, cursor, context, self)".format(_safename(element._fName)))
                    else:
                        code.append("        self._{0} = {1}.read(source, cursor, context, self)".format(_safename(element._fName), _safename(element._fTypeName)))
                        fields.append(_safename(element._fName))
                        recarray.append("out.extend({0}._recarray())".format(_safename(element._fTypeName)))

                else:
                    raise AssertionError(element)

            code.extend(["        if startendcheck:",
                         "            if self.__class__.__name__ == cls.__name__:",
                         "                self.__class__ = cls._versions[classversion]",
                         "            try:",
                         "                _endcheck(start, cursor, cnt)",
                         "            except ValueError:",
                         "                cursor.index = start",
                         "                return Undefined.read(source, cursor, context, parent, cls.__name__)",
                         "        return self"])

            for n, v in sorted(formats.items()):
                code.append("    {0} = {1}".format(n, v))
            for n, v in sorted(dtypes.items()):
                code.append("    {0} = {1}".format(n, v))
            code.append("    _int32 = struct.Struct('>I')")

            code.insert(0, "    _hasreadobjany = {0}".format(hasreadobjany))
            code.insert(0, "    _classversion = {0}".format(streamerinfo._fClassVersion))
            code.insert(0, "    _versions = versions")
            code.insert(0, "    classname = {0}".format(repr(streamerinfo._fName.decode("ascii"))))
            if sys.version_info[0] > 2:
                code.insert(0, "    _classname = {0}".format(repr(streamerinfo._fName)))
            else:
                code.insert(0, "    _classname = b{0}".format(repr(streamerinfo._fName)))
            code.insert(0, "    _fields = [{0}]".format(", ".join(repr(str(x)) for x in fields)))
            code.insert(0, "    @classmethod\n    def _recarray(cls):\n        out = []\n        out.append((' cnt', 'u4'))\n        out.append((' vers', 'u2'))\n        for base in cls._bases:\n            out.extend(base._recarray())\n        {0}\n        return out".format("\n        ".join(recarray)))
            code.insert(0, "    _bases = [{0}]".format(", ".join(bases)))
            code.insert(0, "    _methods = {0}".format("uproot_methods.classes.{0}.Methods".format(pyclassname) if uproot_methods.classes.hasmethods(pyclassname) else "None"))

            if len(bases) == 0:
                bases.append("ROOTStreamedObject")

            if pyclassname == "TTree":
                bases.insert(0, "uproot.tree.TTreeMethods")
            if pyclassname == "TBranch":
                bases.insert(0, "uproot.tree.TBranchMethods")
            if uproot_methods.classes.hasmethods(pyclassname):
                bases.insert(0, "uproot_methods.classes.{0}.Methods".format(pyclassname))

            code.insert(0, "class {0}({1}):".format(pyclassname, ", ".join(bases)))

            if pyclassname in classes:
                versions = classes[pyclassname]._versions
            else:
                versions = {}

            classes["versions"] = versions
            pyclass = _makeclass(streamerinfo._fName, id(streamerinfo), "\n".join(code), classes)
            streamerinfo.pyclass = pyclass
            versions[pyclass._classversion] = pyclass

    return classes

def _makeclass(classname, id, codestr, classes):
    exec(compile(codestr, "<generated from TStreamerInfo {0} at 0x{1:012x}>".format(repr(classname), id), "exec"), classes)
    out = classes[_safename(classname)]
    out._pycode = codestr
    return out

################################################################ built-in ROOT objects for bootstrapping up to streamed classes

class ROOTObject(object):
    # makes __doc__ attribute mutable before Python 3.3
    __metaclass__ = type.__new__(type, "type", (type,), {})

    _copycontext = False

    @property
    def _classname(self):
        return self.__class__.__name__

    @classmethod
    def read(cls, source, cursor, context, parent):
        if cls._copycontext:
            context = context.copy()
        out = cls.__new__(cls)
        out = cls._readinto(out, source, cursor, context, parent)
        out._postprocess(source, cursor, context, parent)
        return out

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        raise NotImplementedError

    def _postprocess(self, source, cursor, context, parent):
        pass

    def __repr__(self):
        if hasattr(self, "_fName"):
            return "<{0} {1} at 0x{2:012x}>".format(self.__class__.__name__, repr(self._fName), id(self))
        else:
            return "<{0} at 0x{1:012x}>".format(self.__class__.__name__, id(self))

class TKey(ROOTObject):
    _classname = b"TKey"
    classname = "TKey"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start = cursor.index

        self._fNbytes, self._fVersion, self._fObjlen, self._fDatime, self._fKeylen, self._fCycle, self._fSeekKey, self._fSeekPdir = cursor.fields(source, self._format_small)
        if self._fVersion > 1000:
            cursor.index = start
            self._fNbytes, self._fVersion, self._fObjlen, self._fDatime, self._fKeylen, self._fCycle, self._fSeekKey, self._fSeekPdir = cursor.fields(source, self._format_big)

        self._fClassName = cursor.string(source)
        self._fName = cursor.string(source)
        self._fTitle = cursor.string(source)

        # if source.size() is not None:
        #     if source.size() - self._fSeekKey < self._fNbytes:
        #         raise ValueError("TKey declares that object {0} has {1} bytes but only {2} remain in the file (after the key)".format(repr(self._fName), self._fNbytes, source.size() - self._fSeekKey))

        # object size != compressed size means it's compressed
        if self._fObjlen != self._fNbytes - self._fKeylen:
            self._source = uproot.source.compressed.CompressedSource(context.compression, source, Cursor(self._fSeekKey + self._fKeylen), self._fNbytes - self._fKeylen, self._fObjlen)
            self._cursor = Cursor(0, origin=-self._fKeylen)

        # otherwise, it's uncompressed
        else:
            self._source = source
            self._cursor = Cursor(self._fSeekKey + self._fKeylen, origin=self._fSeekKey)

        self._context = context
        return self

    _format_small = struct.Struct(">ihiIhhii")
    _format_big   = struct.Struct(">ihiIhhqq")

    def get(self, dismiss=True):
        """Extract the object this key points to.

        Objects are not read or decompressed until this function is explicitly called.
        """

        try:
            return _classof(self._context, self._fClassName).read(self._source, self._cursor.copied(), self._context, self)
        finally:
            if dismiss:
                self._source.dismiss()

def _canonicaltype(name):
    for pattern, replacement in _canonicaltype.patterns:
        name = pattern.sub(replacement, name)
    return name

_canonicaltype.patterns = [
    (re.compile(br"\bChar_t\b"),       b"char"),               # Signed Character 1 byte (char)
    (re.compile(br"\bUChar_t\b"),      b"unsigned char"),      # Unsigned Character 1 byte (unsigned char)
    (re.compile(br"\bShort_t\b"),      b"short"),              # Signed Short integer 2 bytes (short)
    (re.compile(br"\bUShort_t\b"),     b"unsigned short"),     # Unsigned Short integer 2 bytes (unsigned short)
    (re.compile(br"\bInt_t\b"),        b"int"),                # Signed integer 4 bytes (int)
    (re.compile(br"\bUInt_t\b"),       b"unsigned int"),       # Unsigned integer 4 bytes (unsigned int)
    (re.compile(br"\bSeek_t\b"),       b"int"),                # File pointer (int)
    (re.compile(br"\bLong_t\b"),       b"long"),               # Signed long integer 4 bytes (long)
    (re.compile(br"\bULong_t\b"),      b"unsigned long"),      # Unsigned long integer 4 bytes (unsigned long)
    (re.compile(br"\bFloat_t\b"),      b"float"),              # Float 4 bytes (float)
    (re.compile(br"\bFloat16_t\b"),    b"float"),              # Float 4 bytes written with a truncated mantissa
    (re.compile(br"\bDouble_t\b"),     b"double"),             # Double 8 bytes
    (re.compile(br"\bDouble32_t\b"),   b"double"),             # Double 8 bytes in memory, written as a 4 bytes float
    (re.compile(br"\bLongDouble_t\b"), b"long double"),        # Long Double
    (re.compile(br"\bText_t\b"),       b"char"),               # General string (char)
    (re.compile(br"\bBool_t\b"),       b"bool"),               # Boolean (0=false, 1=true) (bool)
    (re.compile(br"\bByte_t\b"),       b"unsigned char"),      # Byte (8 bits) (unsigned char)
    (re.compile(br"\bVersion_t\b"),    b"short"),              # Class version identifier (short)
    (re.compile(br"\bOption_t\b"),     b"const char"),         # Option string (const char)
    (re.compile(br"\bSsiz_t\b"),       b"int"),                # String size (int)
    (re.compile(br"\bReal_t\b"),       b"float"),              # TVector and TMatrix element type (float)
    (re.compile(br"\bLong64_t\b"),     b"long long"),          # Portable signed long integer 8 bytes
    (re.compile(br"\bULong64_t\b"),    b"unsigned long long"), # Portable unsigned long integer 8 bytes
    (re.compile(br"\bAxis_t\b"),       b"double"),             # Axis values type (double)
    (re.compile(br"\bStat_t\b"),       b"double"),             # Statistics type (double)
    (re.compile(br"\bFont_t\b"),       b"short"),              # Font number (short)
    (re.compile(br"\bStyle_t\b"),      b"short"),              # Style number (short)
    (re.compile(br"\bMarker_t\b"),     b"short"),              # Marker number (short)
    (re.compile(br"\bWidth_t\b"),      b"short"),              # Line width (short)
    (re.compile(br"\bColor_t\b"),      b"short"),              # Color number (short)
    (re.compile(br"\bSCoord_t\b"),     b"short"),              # Screen coordinates (short)
    (re.compile(br"\bCoord_t\b"),      b"double"),             # Pad world coordinates (double)
    (re.compile(br"\bAngle_t\b"),      b"float"),              # Graphics angle (float)
    (re.compile(br"\bSize_t\b"),       b"float"),              # Attribute size (float)
    ]

class TStreamerInfo(ROOTObject):
    _classname = b"TStreamerInfo"
    classname = "TStreamerInfo"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        self._fName = _canonicaltype(_nametitle(source, cursor)[0])
        self._fCheckSum, self._fClassVersion = cursor.fields(source, TStreamerInfo._format)
        self._fElements = _readobjany(source, cursor, context, parent)
        assert isinstance(self._fElements, list)
        _endcheck(start, cursor, cnt)
        return self

    _format = struct.Struct(">Ii")

    def show(self, stream=sys.stdout):
        out = "StreamerInfo for class: {0}, version={1}, checksum=0x{2:08x}\n{3}{4}".format(self._fName.decode("ascii"), self._fClassVersion, self._fCheckSum, "\n".join("  " + x.show(stream=None) for x in self._fElements), "\n" if len(self._fElements) > 0 else "")
        if stream is None:
            return out
        else:
            stream.write(out)
            stream.write("\n")

class TStreamerElement(ROOTObject):
    _classname = b"TStreamerElement"
    classname = "TStreamerElement"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)

        self._fOffset = 0
        # https://github.com/root-project/root/blob/master/core/meta/src/TStreamerElement.cxx#L505
        self._fName, self._fTitle = _nametitle(source, cursor)
        self._fType, self._fSize, self._fArrayLength, self._fArrayDim = cursor.fields(source, TStreamerElement._format1)

        if self._classversion == 1:
            n = cursor.field(source, TStreamerElement._format2)
            self._fMaxIndex = cursor.array(source, n, ">i4")
        else:
            self._fMaxIndex = cursor.array(source, 5, ">i4")

        self._fTypeName = _canonicaltype(cursor.string(source))

        if self._fType == 11 and (self._fTypeName == "Bool_t" or self._fTypeName == "bool"):
            self._fType = 18

        if self._classversion <= 2:
            # FIXME
            # self._fSize = self._fArrayLength * gROOT->GetType(GetTypeName())->Size()
            pass

        self._fXmin, self._fXmax, self._fFactor = 0.0, 0.0, 0.0
        if self._classversion == 3:
            self._fXmin, self._fXmax, self._fFactor = cursor.fields(source, TStreamerElement._format3)
        if self._classversion > 3:
            # FIXME
            # if (TestBit(kHasRange)) GetRange(GetTitle(),fXmin,fXmax,fFactor)
            pass

        _endcheck(start, cursor, cnt)
        return self

    _format1 = struct.Struct(">iiii")
    _format2 = struct.Struct(">i")
    _format3 = struct.Struct(">ddd")

    def show(self, stream=sys.stdout):
        out = "{0:15s} {1:15s} offset={2:3d} type={3:2d} {4}".format(self._fName.decode("ascii"), self._fTypeName.decode("ascii"), self._fOffset, self._fType, self._fTitle.decode("ascii"))
        if stream is None:
            return out
        else:
            stream.write(out)
            stream.write("\n")

class TStreamerArtificial(TStreamerElement):
    _classname = b"TStreamerArtificial"
    classname = "TStreamerArtificial"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerArtificial, self)._readinto(self, source, cursor, context, parent)
        _endcheck(start, cursor, cnt)
        return self

class TStreamerBase(TStreamerElement):
    _classname = b"TStreamerBase"
    classname = "TStreamerBase"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerBase, self)._readinto(self, source, cursor, context, parent)
        if self._classversion >= 2:
            self._fBaseVersion = cursor.field(source, TStreamerBase._format)
        _endcheck(start, cursor, cnt)
        return self

    _format = struct.Struct(">i")

class TStreamerBasicPointer(TStreamerElement):
    _classname = b"TStreamerBasicPointer"
    classname = "TStreamerBasicPointer"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerBasicPointer, self)._readinto(self, source, cursor, context, parent)
        self._fCountVersion = cursor.field(source, TStreamerBasicPointer._format)
        self._fCountName = cursor.string(source)
        self._fCountClass = cursor.string(source)
        _endcheck(start, cursor, cnt)
        return self

    _format = struct.Struct(">i")

class TStreamerBasicType(TStreamerElement):
    _classname = b"TStreamerBasicType"
    classname = "TStreamerBasicType"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerBasicType, self)._readinto(self, source, cursor, context, parent)

        if uproot.const.kOffsetL < self._fType < uproot.const.kOffsetP:
            self._fType -= uproot.const.kOffsetL

        basic = True
        if self._fType in (uproot.const.kBool, uproot.const.kUChar, uproot.const.kChar):
            self._fSize = 1
        elif self._fType in (uproot.const.kUShort, uproot.const.kShort):
            self._fSize = 2
        elif self._fType in (uproot.const.kBits, uproot.const.kUInt, uproot.const.kInt, uproot.const.kCounter):
            self._fSize = 4
        elif self._fType in (uproot.const.kULong, uproot.const.kULong64, uproot.const.kLong, uproot.const.kLong64):
            self._fSize = 8
        elif self._fType in (uproot.const.kFloat, uproot.const.kFloat16):
            self._fSize = 4
        elif self._fType in (uproot.const.kDouble, uproot.const.kDouble32):
            self._fSize = 8
        elif self._fType == uproot.const.kCharStar:
            self._fSize = numpy.dtype(numpy.intp).itemsize
        else:
            basic = False

        if basic and self._fArrayLength > 0:
            self._fSize *= self._fArrayLength

        _endcheck(start, cursor, cnt)
        return self

class TStreamerLoop(TStreamerElement):
    _classname = b"TStreamerLoop"
    classname = "TStreamerLoop"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerLoop, self)._readinto(self, source, cursor, context, parent)
        self._fCountVersion = cursor.field(source, TStreamerLoop._format)
        self._fCountName = cursor.string(source)
        self._fCountClass = cursor.string(source)
        _endcheck(start, cursor, cnt)
        return self

    _format = struct.Struct(">i")

class TStreamerObject(TStreamerElement):
    _classname = b"TStreamerObject"
    classname = "TStreamerObject"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerObject, self)._readinto(self, source, cursor, context, parent)
        _endcheck(start, cursor, cnt)
        return self

class TStreamerObjectAny(TStreamerElement):
    _classname = b"TStreamerObjectAny"
    classname = "TStreamerObjectAny"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerObjectAny, self)._readinto(self, source, cursor, context, parent)
        _endcheck(start, cursor, cnt)
        return self

class TStreamerObjectAnyPointer(TStreamerElement):
    _classname = b"TStreamerObjectAnyPointer"
    classname = "TStreamerObjectAnyPointer"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerObjectAnyPointer, self)._readinto(self, source, cursor, context, parent)
        _endcheck(start, cursor, cnt)
        return self

class TStreamerObjectPointer(TStreamerElement):
    _classname = b"TStreamerObjectPointer"
    classname = "TStreamerObjectPointer"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerObjectPointer, self)._readinto(self, source, cursor, context, parent)
        _endcheck(start, cursor, cnt)
        return self

class TStreamerSTL(TStreamerElement):
    _classname = b"TStreamerSTL"
    classname = "TStreamerSTL"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerSTL, self)._readinto(self, source, cursor, context, parent)

        self._fSTLtype, self._fCtype = cursor.fields(source, TStreamerSTL._format)

        if self._fSTLtype == uproot.const.kSTLmultimap or self._fSTLtype == uproot.const.kSTLset:
            if self._fTypeName.startswith(b"std::set") or self._fTypeName.startswith(b"set"):
                self._fSTLtype = uproot.const.kSTLset
            elif self._fTypeName.startswith(b"std::multimap") or self._fTypeName.startswith(b"multimap"):
                self._fSTLtype = uproot.const.kSTLmultimap

        _endcheck(start, cursor, cnt)
        return self

    @classmethod
    def vector(cls, fType, fTypeName):
        self = cls.__new__(cls)
        self._fSTLtype = uproot.const.kSTLvector
        self._fCtype = fType
        self._fTypeName = b"vector<" + fTypeName + b">"
        return self

    _format = struct.Struct(">ii")

class TStreamerSTLstring(TStreamerSTL):
    _classname = b"TStreamerSTLstring"
    classname = "TStreamerSTLstring"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerSTLstring, self)._readinto(self, source, cursor, context, parent)
        _endcheck(start, cursor, cnt)
        return self

class TStreamerString(TStreamerElement):
    _classname = b"TStreamerString"
    classname = "TStreamerString"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        super(TStreamerString, self)._readinto(self, source, cursor, context, parent)
        _endcheck(start, cursor, cnt)
        return self

################################################################ streamed classes (with some overrides)

class ROOTStreamedObject(ROOTObject):
    _fields = []

    @classmethod
    def _members(cls):
        out = []
        for t in cls.__bases__:
            if issubclass(t, ROOTStreamedObject):
                out.extend(t._members())
        out.extend(cls._fields)
        return out

    @classmethod
    def _recarray(cls):
        raise ValueError("not a recarray")

    @classmethod
    def _recarray_dtype(cls, cntvers=False, tobject=True):
        dtypesin = cls._recarray()
        dtypesout = []
        used = set()
        allhidden = True
        for name, dtype in dtypesin:
            if name in used:
                i = 2
                trial = name + str(i)
                while trial in used:
                    i += 1
                    trial = name + str(i)
                name = trial

            if (cntvers or not (name == " cnt" or name == " vers")) and (tobject or not (name == " fUniqueID" or name == " fBits")):
                dtypesout.append((name, dtype))
                used.add(name)
                if not name.startswith(" "):
                    allhidden = False

        if allhidden:
            raise ValueError("not a recarray")

        return numpy.dtype(dtypesout)

class TObject(ROOTStreamedObject):
    _classname = b"TObject"
    classname = "TObject"

    @classmethod
    def _recarray(cls):
        return [(" fBits", numpy.dtype(">u8")), (" fUniqueID", numpy.dtype(">u8"))]

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        _skiptobj(source, cursor)
        return self

class TString(bytes, ROOTStreamedObject):
    _classname = b"TString"
    classname = "TString"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        return TString(cursor.string(source))

    def __str__(self):
        return self.decode("utf-8", "replace")

class TNamed(TObject):
    _classname = b"TNamed"
    classname = "TNamed"
    _fields = ["fName", "fTitle"]

    @classmethod
    def _recarray(cls):
        raise ValueError("not a recarray")

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        TObject._readinto(self, source, cursor, context, parent)
        self._fName = cursor.string(source)
        self._fTitle = cursor.string(source)
        _endcheck(start, cursor, cnt)
        return self

class TObjArray(list, ROOTStreamedObject):
    _classname = b"TObjArray"
    classname = "TObjArray"

    @classmethod
    def read(cls, source, cursor, context, parent, asclass=None):
        if cls._copycontext:
            context = context.copy()
        out = cls.__new__(cls)
        out = cls._readinto(out, source, cursor, context, parent, asclass=asclass)
        out._postprocess(source, cursor, context, parent)
        return out

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent, asclass=None):
        start, cnt, self._classversion = _startcheck(source, cursor)
        _skiptobj(source, cursor)
        name = cursor.string(source)
        size, low = cursor.fields(source, struct.Struct(">ii"))
        self.extend([_readobjany(source, cursor, context, parent, asclass=asclass) for i in range(size)])
        _endcheck(start, cursor, cnt)
        return self

class TObjString(bytes, ROOTStreamedObject):
    _classname = b"TObjString"
    classname = "TObjString"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        _skiptobj(source, cursor)
        string = cursor.string(source)
        _endcheck(start, cursor, cnt)
        return TObjString(string)

    def __str__(self):
        return self.decode("utf-8", "replace")

class TList(list, ROOTStreamedObject):
    _classname = b"TList"
    classname = "TList"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        _skiptobj(source, cursor)
        name = cursor.string(source)
        size = cursor.field(source, struct.Struct(">i"))
        for i in range(size):
            self.append(_readobjany(source, cursor, context, parent))
            n = cursor.field(source, TList._format_n)  # ignore option
            cursor.bytes(source, n)
        _endcheck(start, cursor, cnt)
        return self
    _format_n = struct.Struct(">B")

class THashList(TList):
    _classname = b"THashList"
    classname = "THashList"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        TList._readinto(self, source, cursor, context, parent)
        return self

class TRef(ROOTStreamedObject):
    _classname = b"TRef"
    classname = "TRef"

    _format1 = struct.Struct(">xxIxxxxxx")

    def __init__(self, id):
        self.id = id

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        self.id = cursor.field(source, self._format1)
        return self

    def __repr__(self):
        return "<TRef {0}>".format(self.id)

    @classmethod
    def _recarray(cls):
        out = []
        out.append(("pidf", ">u2"))
        out.append(("id", ">u4"))
        out.append((" other", "S6"))
        return out

TRef._methods = TRef
TRef._arraymethods = None
TRef._fromrow = lambda row: TRef(row["id"])

class TRefArray(list, ROOTStreamedObject):
    _classname = b"TRefArray"
    classname = "TRefArray"

    _format1 = struct.Struct(">i")
    _dtype = numpy.dtype(">i4")

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        cursor.skip(10)
        self.name = cursor.string(source)
        self.length = cursor.field(source, self._format1)
        cursor.skip(6)
        self.extend(cursor.array(source, self.length, self._dtype))
        _endcheck(start, cursor, cnt)
        return self

    @property
    def nbytes(self):
        return len(self) * self._dtype.itemsize

    def tostring(self):
        return numpy.asarray(self, dtype=self._dtype).tostring()

class TArray(list, ROOTStreamedObject):
    _classname = b"TArray"
    classname = "TArray"

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        length = cursor.field(source, TArray._format)
        self.extend(cursor.array(source, length, self._dtype))
        return self
    _format = struct.Struct(">i")

    @property
    def nbytes(self):
        return len(self) * self._dtype.itemsize

    def tostring(self):
        return numpy.asarray(self, dtype=self._dtype).tostring()

class TArrayC(TArray):
    _classname = b"TArrayC"
    classname = "TArrayC"
    _dtype = numpy.dtype(">i1")

class TArrayS(TArray):
    _classname = b"TArrayS"
    classname = "TArrayS"
    _dtype = numpy.dtype(">i2")

class TArrayI(TArray):
    _classname = b"TArrayI"
    classname = "TArrayI"
    _dtype = numpy.dtype(">i4")

class TArrayL(TArray):
    _classname = b"TArrayL"
    classname = "TArrayL"
    _dtype = numpy.dtype(numpy.int_).newbyteorder(">")

class TArrayL64(TArray):
    _classname = b"TArrayL64"
    classname = "TArrayL64"
    _dtype = numpy.dtype(">i8")

class TArrayF(TArray):
    _classname = b"TArrayF"
    classname = "TArrayF"
    _dtype = numpy.dtype(">f4")

class TArrayD(TArray):
    _classname = b"TArrayD"
    classname = "TArrayD"
    _dtype = numpy.dtype(">f8")

# FIXME: I want to generalize this. It's the first example of a class that doesn't
# follow the usual pattern. The full 11 bytes are
#
#     "40 00 00 07 00 00 1a a1 2f 10 00"
#
# I'm reasonably certain the first "40 00 00 07" is count with a kByteCountMask.
# The next "00 00" probably isn't the version, since the streamer said it's version 1.
# I'm also reasonably certain that the last byte is the fIOBits data.
# That leaves 4 bytes unaccounted for.
class ROOT_3a3a_TIOFeatures(ROOTStreamedObject):
    _classname = b"ROOT::TIOFeatures"
    classname = "ROOT::TIOFeatures"
    _fields = ["fIOBits"]

    @classmethod
    def _readinto(cls, self, source, cursor, context, parent):
        start, cnt, self._classversion = _startcheck(source, cursor)
        cursor.skip(4)
        self._fIOBits = cursor.field(source, ROOT_3a3a_TIOFeatures._format1)
        _endcheck(start, cursor, cnt)
        return self

    _format1 = struct.Struct(">B")

class ROOT_3a3a_Experimental_3a3a_RNTuple(ROOTStreamedObject):
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
        start, cnt, self._classversion = _startcheck(source, cursor)
        cursor.skip(4)
        self._fVersion, self._fSize, self._fSeekHeader, self._fNBytesHeader, self._fLenHeader, self._fSeekFooter, self._fNBytesFooter, self._fLenFooter, self._fReserved = cursor.fields(source, ROOT_3a3a_Experimental_3a3a_RNTuple._format1)
        return self

    _format1 = struct.Struct(">IIQIIQIIQ")

class Undefined(ROOTStreamedObject):
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
        start, cnt, self._classversion = _startcheck(source, cursor)
        if cnt is None:
            raise TypeError("cannot read objects of type {0} and cannot even skip over this one (returning Undefined) because its size is not known\n  in file: {1}".format("???" if self._classname is None else self._classname.decode("ascii"), context.sourcepath))

        cursor.skip(cnt - 6)
        _endcheck(start, cursor, cnt)
        return self

    def __repr__(self):
        if self._classname is not None:
            return "<{0} (failed to read {1} version {2}) at 0x{3:012x}>".format(self.__class__.__name__, repr(self._classname), self._classversion, id(self))
        else:
            return "<{0} at 0x{1:012x}>".format(self.__class__.__name__, id(self))

builtin_classes = {"uproot_methods": uproot_methods,
                   "TObject":        TObject,
                   "TString":        TString,
                   "TNamed":         TNamed,
                   "TObjArray":      TObjArray,
                   "TObjString":     TObjString,
                   "TList":          TList,
                   "THashList":      THashList,
                   "TRef":           TRef,
                   "TArray":         TArray,
                   "TArrayC":        TArrayC,
                   "TArrayS":        TArrayS,
                   "TArrayI":        TArrayI,
                   "TArrayL":        TArrayL,
                   "TArrayL64":      TArrayL64,
                   "TArrayF":        TArrayF,
                   "TArrayD":        TArrayD,
                   "TRefArray":      TRefArray,
                   "ROOT_3a3a_TIOFeatures": ROOT_3a3a_TIOFeatures,
                   "ROOT_3a3a_Experimental_3a3a_RNTuple": ROOT_3a3a_Experimental_3a3a_RNTuple}

builtin_skip =    {"TBranch":    ["fBaskets"],
                   "TTree":      ["fUserInfo", "fBranchRef"]}
