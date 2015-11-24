"""Testing the ABX.distances subpackage"""

import numpy as np

from ABXpy.distances.metrics.utw import utw

def test_utw():
    metric = lambda x, y: np.sum(np.abs(x-y), axis=1)
    x = np.array([[0, 0],
                  [0, -1],
                  [0, 0],
                  [4, 0],
                  [0, 1],
                  [-4, 5],
                  [5, 0]])
    y = np.array([[0, 1],
                  [0, 1],
                  [0, -2],
                  [1, 1]])

    assert(utw(x, y, metric) == 26.5)
    assert(utw(y, x, metric) == 26.5)
