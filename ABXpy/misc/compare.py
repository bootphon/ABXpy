# -*- coding: utf-8 -*-
"""Functions for comparing two files
"""
"""
Created on Thu Apr 24 18:05:41 2014

@author: thiolliere
@author: Mathieu Bernard
"""

import filecmp
import subprocess

def cmp(f1, f2):
    """Compare two files.

    Return True if f1 and f2 are equal, False else. Equality is
    checked only on file descriptors (see os.stat).
    """
    return filecmp.cmp(f1, f2, shallow=True)

def h5cmp(f1, f2):
    """Compare two HDF5 files.

    Return True if f1 and f2 are equal, False else. Equality is
    checked with the 'h5diff' external process.
    """

    try:
        out = subprocess.check_output(['h5diff', f1, f2])
    except subprocess.CalledProcessError:
        return False

    if out:
        return False
    return True
