# -*- coding: utf-8 -*-
"""
Created on Tue Oct 29 00:29:00 2013

:author: Thomas Schatz
"""

import numpy as np


def fit_integer_type(n, is_signed=True):
    """Determine the minimal space needed to store integers of maximal value n
    """

    if is_signed:
        m = 1
        types = [np.int8, np.int16, np.int32, np.int64]
    else:
        m = 0
        types = [np.uint8, np.uint16, np.uint32, np.uint64]

    if n < 2**(8-m):
        return types[0]
    elif n < 2**(16-m):
        return types[1]
    elif n < 2**(32-m):
        return types[2]
    elif n < 2**(64-m):
        return types[3]
    else:
        raise ValueError('Values are too big to be represented by 64 bits \
            integers!')
