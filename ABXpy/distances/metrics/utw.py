import numpy as np

def utw(x, y, div):
    """Uniform Time Warping

    Parameters
    ----------
    x : numpy.Array
        Size m_x by n
    y : numpy.Array
        Size m_y by n
    div : function
        Takes two m by n arrays and returns a m by 1 array
        containing the distances between rows 1, rows 2, ...,
        rows m of the two arrays. Does not need to be a metric
        in the mathematical sense

    Returns
    -------
    dis : float
        The UTW distance between x and y according to
        distance function div
    """
    if x.shape[0] > y.shape[0]:
        z = x, y
        y, x = z
    n1 = x.shape[0]
    n2 = y.shape[0]
    i_half, j_half, i_whole, j_whole = distance_coordinates(n1, n2)
    dis = 0
    if i_half.size > 0:
        dis = dis + np.sum(div(x[i_half, :], y[j_half, :])) / 2.
    if i_whole.size > 0:
        dis = dis + np.sum(div(x[i_whole, :], y[j_whole, :]))
    return dis


def distance_coordinates(n1, n2):
    assert(n1 <= n2)
    l1 = np.arange(n2)
    l2 = n1/np.float(n2)*(np.arange(n2)+0.5)
    l3 = np.floor(l2).astype(np.int)
    integers = np.where(l2 == l3)[0]
    non_integers = np.where(l2 != l3)[0]
    l3i = l3[integers]
    l1i = l1[integers]
    i_half = np.concatenate([l3i-1, l3i])
    j_half = np.concatenate([l1i, l1i])
    i_whole = l3[non_integers]
    j_whole = l1[non_integers]
    return i_half, j_half, i_whole, j_whole


# def test():
#     metric = lambda x, y: np.sum(np.abs(x-y), axis=1)
#     x = np.array([[0, 0],
#                   [0, -1],
#                   [0, 0],
#                   [4, 0],
#                   [0, 1],
#                   [-4, 5],
#                   [5, 0]])
#     y = np.array([[0, 1],
#                   [0, 1],
#                   [0, -2],
#                   [1, 1]])
#     assert(utw(x, y, metric) == 26.5)
#     assert(utw(y, x, metric) == 26.5)

# test()
