import ABXpy.distances.metrics.dtw as dtw
import ABXpy.distances.metrics.cosine as cosine
import ABXpy.distances.metrics.kullback_leibler as kullback_leibler
import numpy as np


def dtw_cosine(x, y):
    """ Dynamic time warping cosine distance

    The "feature" dimension is along the columns and the "time"
    dimension along the lines of arrays x and y
    """
    if x.shape[0] > 0 and y.shape[0] > 0:
        # x and y are not empty
        d = dtw.dtw(x, y, cosine.cosine_distance)
    elif x.shape[0] == y.shape[0]:
        # both x and y are empty
        d = 0
    else:
        # x or y is empty
        d = np.inf
    return d


def dtw_kl_divergence(x, y):
    """ Kullback-Leibler divergence
    """
    if x.shape[0] > 0 and y.shape[0] > 0:
        d = dtw.dtw(x, y, kullback_leibler.kl_divergence)
    elif x.shape[0] == y.shape[0]:
        d = 0
    else:
        d = np.inf
    return d

