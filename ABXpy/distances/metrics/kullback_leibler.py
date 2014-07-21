# -*- coding: utf-8 -*-

import numpy as np


def kl_ptwise(x, y):
    return np.sum(x * (np.log(x) - np.log(y)))


def js_ptwise(x, y):
    m = (x + y) / 2
    return 0.5 * kl_ptwise(x, m) + 0.5 * kl_ptwise(y, m)


def __kl_divergence(x, y):
    """ just the KL-div """
    pq = np.dot(x, np.log(y.transpose()))
    pp = np.tile(np.sum(x * np.log(x), axis=1).reshape(x.shape[0], 1), (1, y.shape[0]))
    return pp - pq


def kl_divergence(x, y, thresholded=True, symmetrized=True, normalize=True):
    """ Kullback-Leibler divergence 
    x and y should be 2D numpy arrays with "times" on the lines and "features" on the columns
     - thresholded=True => means we add an epsilon to all the dimensions/values
                           AND renormalize inputs.
     - symmetrized=True => uses the symmetrized KL (0.5 x->y + 0.5 y->x).
     - normalize=True => normalize the inputs so that lines sum to one.
    """
    assert (x.dtype == np.float64 and y.dtype == np.float64) or (x.dtype == np.float32 and y.dtype == np.float32)
    if normalize:
        x /= x.sum(1).reshape(x.shape[0], 1)
        y /= y.sum(1).reshape(y.shape[0], 1)
    if thresholded:
        eps = np.finfo(x.dtype).eps
        x = x+eps
        y = y+eps
        x /= x.sum(1).reshape(x.shape[0], 1)
        y /= y.sum(1).reshape(y.shape[0], 1)
    res = __kl_divergence(x, y)
    if symmetrized:
        res = 0.5 * res + 0.5 * __kl_divergence(y, x).transpose()
    return np.float64(res)


def js_divergence(x, y, normalize=True):
    """ Jensen-Shannon divergence 
    x and y should be 2D numpy arrays with "times" on the lines and "features" on the columns
     - normalize=True => normalize the inputs so that lines sum to one.
    """
    assert (x.dtype == np.float64 and y.dtype == np.float64) or (x.dtype == np.float32 and y.dtype == np.float32)
    if normalize:
        x /= x.sum(1).reshape(x.shape[0], 1)
        y /= y.sum(1).reshape(y.shape[0], 1)
    xx = np.tile(x, (y.shape[0], 1, 1)).transpose((1, 0, 2))
    yy = np.tile(y, (x.shape[0], 1, 1))
    m = (xx + yy) / 2
    x_m = np.sum(xx * np.log(m), axis=2)
    y_m = np.sum(yy * np.log(m), axis=2)
    x_x = np.tile(np.sum(x * np.log(x), axis=1).reshape(x.shape[0], 1), (1, y.shape[0]))
    y_y = np.tile(np.sum(y * np.log(y), axis=1).reshape(y.shape[0], 1), (1, x.shape[0])).transpose()
    res = 0.5 * (x_x - x_m) + 0.5 * (y_y - y_m)
    return np.float64(res)
    # division by zero
    


def sqrt_js_divergence(x, y):
    return np.sqrt(js_divergence(x, y))


def is_distance(x, y):
    """ Itakura-Saito distance 
    x and y should be 2D numpy arrays with "times" on the lines and "features" on the columns
    """
    assert (x.dtype == np.float64 and y.dtype == np.float64) or (x.dtype == np.float32 and y.dtype == np.float32)
    #TODO


