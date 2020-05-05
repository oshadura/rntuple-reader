#!/usr/bin/env python

import os

import pytest

import rntuple


class Test(object):
    
    def test_open_file_staff(self):
        with pytest.raises(Exception) as execinfo:
            raise Exception('We cant open file!')
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
    
    def test_open_file_vector(self):
        with pytest.raises(Exception) as execinfo:
            raise Exception('We cant open file!')
        f = rntuple.open("tests/ntpl002_vector.root")
        rfile = f["F"]
        assert rfile._fVersion == 0
        assert rfile._fSize == 48
        assert rfile._fSeekHeader == 854
        assert rfile._fNBytesHeader == 537
        assert rfile._fLenHeader == 2495
        assert rfile._fSeekFooter == 72369
        assert rfile._fNBytesFooter == 285
        assert rfile._fLenFooter == 804
        assert rfile._fReserved == 0
        
    def test_open_file_lhcb_opendata(self):
        with pytest.raises(Exception) as execinfo:
            raise Exception('We cant open file!')
        f = rntuple.open("tests/ntpl003_lhcbOpenData_1000.root")
        rfile = f["DecayTree"]
        assert rfile._fVersion == 0
        assert rfile._fSize == 48
        assert rfile._fSeekHeader == 854
        assert rfile._fNBytesHeader == 537
        assert rfile._fLenHeader == 2495
        assert rfile._fSeekFooter == 72369
        assert rfile._fNBytesFooter == 285
        assert rfile._fLenFooter == 804
        assert rfile._fReserved == 0


    def test_open_file_dimuon(self):
        with pytest.raises(Exception) as execinfo:
            raise Exception('We cant open file!')
        f = rntuple.open("tests/ntpl004_dimuon_1000.root")
        rfile = f["Events"]
        assert rfile._fVersion == 0
        assert rfile._fSize == 48
        assert rfile._fSeekHeader == 854
        assert rfile._fNBytesHeader == 537
        assert rfile._fLenHeader == 2495
        assert rfile._fSeekFooter == 72369
        assert rfile._fNBytesFooter == 285
        assert rfile._fLenFooter == 804
        assert rfile._fReserved == 0
