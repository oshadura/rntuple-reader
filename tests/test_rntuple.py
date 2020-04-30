#!/usr/bin/env python

import pytest

import rntuple

import os

class Test(object):
    
    def test_open_file(self):
        with pytest.raises(Exception) as execinfo:
            raise Exception('We cant open file!')
        print(os.getcwd())
        f = rntuple.open("tests/ntpl001_staff.root")
        rfile = f["Staff"]
        assert rfile._fVersion == 0
        assert rfile._fSize == 48
        assert rfile._fSeekHeader == 854
        assert rfile._fNBytesHeader == 537
        assert rfile._fLenHeader == 2495
        assert rfile._fSeekFooter == 72369
        assert rfile._fNBytesFooter == 285
        assert rfile._fLenFooter == 804
        assert rfile._fReserved == 0
