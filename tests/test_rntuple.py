#!/usr/bin/env python

import pytest

import rntuple


class Test(object):
    
    
    def test_open_file(self):
        with pytest.raises(Exception) as execinfo:
            raise Exception('We cant open file!')
        assert rntuple.open("data-samples/ntpl001_staff.root") == True
