"""Generate test files for the test functions"""

import filecmp
import h5features
import numpy as np
import os
import pandas
import subprocess
from past.builtins import xrange


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
    if out:
        return False
    else:
        return True


def csv_cmp(f1, f2, sep='\t'):
    """Returns True if the 2 CSV files are equals

    The comparison is not sensitive to the columns order.

    """
    csv1 = pandas.read_csv(f1, sep=sep)
    csv1 = csv1.reindex(sorted(csv1.columns), axis=1)

    csv2 = pandas.read_csv(f2, sep=sep)
    csv2 = csv2.reindex(sorted(csv2.columns), axis=1)

    return csv1.to_csv().split('\n').sort() == csv2.to_csv().split('\n').sort()
