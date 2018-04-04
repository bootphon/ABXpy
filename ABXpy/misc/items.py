from __future__ import print_function
# -*- coding: utf-8 -*-
"""Generate test files for the test functions
"""
"""
Created on Thu Apr 24 18:05:41 2014

@author: thiolliere
"""

import numpy as np
import sys
import os
import filecmp
import subprocess
from past.builtins import xrange
# import h5py
# import numpy as np
# from ys.mods import load
try:
    import h5features
except ImportError:
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__)))), 'h5features'))
    import h5features


def generate_testitems(base, n, repeats=0, name='data.item'):
    """Minimal item file generator for task.py"""
    dim_i, dim_j = base ** n * (repeats + 1) + 1, n + 4

    def fun(i, j):
        if i == 0:
            if j < 4:
                return ['#file', 'onset', 'offset', '#src'][j]
            else:
                return 'c%s' % (j - 4)
        elif j < 4:
            return 'snfi'[j] + str(i - 1)
        else:
            i -= 1
            j -= 4
            return i // (base ** j) % base

    res = [[fun(i, j) for j in range(dim_j)]
           for i in range(dim_i)]
    np.savetxt(name, res, delimiter=' ', fmt='%s')


def generate_named_testitems(base, n, repeats=0, name='data.item'):
    """Extended item file generator
    """

    dim_i, dim_j = base ** n * (repeats + 1) + 1, n + 4

    def fun(i, j):
        if i == 0:
            if j < 4:
                return ['#file', 'onset', 'offset', '#item'][j]
            else:
                return 'c%s' % (j - 4)
        elif j == 0:
            return 's%s' % (i - 1)
        elif j in [1, 2]:
            return 0
        elif j == 3:
            return 'i%s' % (i-1)
        else:
            i -= 1
            j -= 4
            return 'c%s_v%s' % (j, i // (base ** j) % base)

    res = [[fun(i, j) for j in range(dim_j)]
           for i in range(dim_i)]
    np.savetxt(name, res, delimiter=' ', fmt='%s')


def generate_features(n_files, n_feat=2, max_frames=3, name='data.features'):
    """Random feature file generator
    """
    if os.path.exists(name):
        os.remove(name)
    features = []
    times = []
    files = []
    for i in xrange(n_files):
        n_frames = np.random.randint(max_frames) + 1
        features.append(np.random.randn(n_frames, n_feat))
        times.append(np.linspace(0, 1, n_frames))
        files.append('s%d' % i)
    h5features.write(name, 'features', files, times, features)


def generate_db_and_feat(base, n, repeats=0, name_db='data.item', n_feat=2,
                         max_frames=3, name_feat='data.features'):
    """Item and feature files generator
    """
    generate_named_testitems(base, n, repeats, name_db)
    print(name_db)
    n_files = (base ** n) * (repeats + 1)
    generate_features(n_files, n_feat, max_frames, name_feat)


def cmp(f1, f2):
    return filecmp.cmp(f1, f2, shallow=True)


def h5cmp(f1, f2):
    try:
        out = subprocess.check_output(['h5diff', f1, f2])
    except subprocess.CalledProcessError:
        return False
    # print out
    if out:
        return False
    else:
        return True


def csv_cmp(f1, f2):
    with open(f1) as f1in, open(f2) as f2in:
        f1_content = f1in.readlines()
        f2_content = f2in.readlines()
    f1_content.sort()
    f2_content.sort()
    return np.all(f1_content == f2_content)
