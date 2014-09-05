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
try:
    import h5features
except ImportError:
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__)))), 'h5features'))
    import h5features


def generate_testitems(base, n, repeats=0, name='data.item'):
    """Minimal item file generator for task.py
    """
    res = np.empty((base ** n * (repeats + 1) + 1, n + 2), dtype='|S5')
    res[0, 0] = '#item'
    res[0, 1] = '#src'

    for j, _ in enumerate(res[0, 2:]):
        res[0, j + 2] = 'c' + str(j)

    for i, _ in enumerate(res[1:, 0]):
        res[i + 1, 0] = 's' + str(i)

    for i, _ in enumerate(res[1:, 1]):
        res[i + 1, 1] = 'i' + str(i)

    aux = res[1:, 2:]
    for (i, j), _ in np.ndenumerate(aux):
        aux[i][j] = (i / (base ** j) % base)

    np.savetxt(name, res, delimiter=' ', fmt='%s')


def generate_named_testitems(base, n, repeats=0, name='data.item'):
    """Extended item file generator
    """
    res = np.empty((base ** n * (repeats + 1) + 1, n + 4), dtype='|S6')
    res[0, 0] = '#file'
    res[0, 1] = 'onset'
    res[0, 2] = 'offset'
    res[0, 3] = '#item'

    for j, _ in enumerate(res[0, 4:]):
        res[0, j + 4] = 'c' + str(j)

    for i, _ in enumerate(res[1:, 0]):
        res[i + 1, 0] = 's' + str(i)

    res[1:, 1] = np.zeros(res[1:, 1].shape)
    res[1:, 2] = np.zeros(res[1:, 2].shape)

    for i, _ in enumerate(res[1:, 3]):
        res[i + 1, 3] = 'i' + str(i)

    aux = res[1:, 4:]
    for (i, j), _ in np.ndenumerate(aux):
        aux[i][j] = 'c' + str(j) + '_v' + str(i / (base ** j) % base)

    np.savetxt(name, res, delimiter=' ', fmt='%s')


def generate_features(n_files, n_feat=2, max_frames=3, name='data.features'):
    """Random feature file generator
    """
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
    print name_db
    n_files = (base ** n) * (repeats + 1)
    generate_features(n_files, n_feat, max_frames, name_feat)
