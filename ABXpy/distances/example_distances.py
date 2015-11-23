import numpy as np

import ABXpy.distances.metrics.dtw as dtw
import ABXpy.distances.metrics.cosine as cosine
import ABXpy.distances.metrics.kullback_leibler as kullback_leibler


def dtw_wrapper(x, y, dist):
    if x.shape[0] > 0 and y.shape[0] > 0:
        # x and y are not empty
        d = dtw.dtw(x, y, dist)
    elif x.shape[0] == y.shape[0]:
        # both x and y are empty
        d = 0
    else:
        # x or y is empty
        d = np.inf
    return d


def dtw_cosine(x, y):
    """ Dynamic time warping cosine distance

    The "feature" dimension is along the columns and the "time"
    dimension along the lines of arrays x and y
    """
    return dtw_wrapper(x, y, cosine.cosine_distance)


def dtw_kl_divergence(x, y):
    """ Kullback-Leibler divergence"""
    return dtw_wrapper(x, y, kullback_leibler.kl_divergence)
