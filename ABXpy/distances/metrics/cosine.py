# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 01:47:42 2014

@author: Thomas Schatz
"""
import numpy as np

# FIXME change name to just distance ou distance_matrix?  compute
# cosine distances between all possible pairs of lines in the x and y
# matrix x and y should be 2D numpy arrays with "features" on the
# lines and "times" on the columns x, y must be float arrays


def cosine_distance(x, y):
    assert (x.dtype == np.float64 and y.dtype == np.float64) or (
        x.dtype == np.float32 and y.dtype == np.float32)
    x2 = np.sqrt(np.sum(x ** 2, axis=1))
    y2 = np.sqrt(np.sum(y ** 2, axis=1))
    ix = x2 == 0.
    iy = y2 == 0.
    d = np.dot(x, y.T) / (np.outer(x2, y2))
    # Rounding of floating point numbers can give values outside the range [-1, 1]
    d = np.clip(d, -1, 1)
    # DPX: to prevent the stupid scipy to collapse the array into scalar
    if d.shape == (1, 1):
        d = np.array([[np.float64(np.lib.scimath.arccos(d[0, 0]) / np.pi)]]).reshape((1, 1))
    else:
        # costly in time (half of the time), so check if really useful for dtw
        d = np.float64(np.lib.scimath.arccos(d) / np.pi)

    d[ix, :] = 1.
    d[:, iy] = 1.
    for i in np.where(ix)[0]:
        d[i, iy] = 0.
    assert np.all(d >= 0)
    return d


def normalize_cosine_distance(x, y):
    x /= x.sum(1).reshape(x.shape[0], 1)
    y /= y.sum(1).reshape(y.shape[0], 1)
    return cosine_distance(x, y)
