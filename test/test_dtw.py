"""Module for testing the dtw module"""

import ABXpy.distances.metrics.dtw as dtw
import numpy as np


def test_small():
    res = dtw._dtw(1, 1, np.ones((1, 1)), normalized=False)
    assert res == 1

    res = dtw._dtw(1, 1, np.ones((1, 1)), normalized=True)
    assert res == 1


def test_normalized():
    dists = np.ones((5, 5)) * 2
    dists = dists - np.diag(np.ones((5,)))
    res = dtw._dtw(5, 5, dists, normalized=True)
    assert res == 1

    dists_start = np.ones((5, 2)) * 2
    dists_start[0, :] = 1
    dists_start = np.concatenate([dists_start, dists], axis=1)
    res = dtw._dtw(5, 7, dists_start, normalized=True)
    assert res == 1

    dists_start = np.ones((2, 5)) * 2
    dists_start[:, 0] = 1
    dists_start = np.concatenate([dists_start, dists], axis=0)
    res = dtw._dtw(7, 5, dists_start, normalized=True)
    assert res == 1

    dists_mid = np.ones((5, 2)) * 2
    dists_mid[3, :] = 1
    dists_mid = np.concatenate([dists[:, :3], dists_mid, dists[:, 3:]], axis=1)
    res = dtw._dtw(5, 7, dists_mid, normalized=True)
    assert res == 1
