"""Generate an artificial dataset for testing ABXpy.

Item and feature generation are provided.
This file is a fork of misc/items.py.

@author: Mathieu Bernard
"""

import numpy as np
import os.path
import h5features


def item(base, n, repeats=0, name=''):
    """Item data generator.

    Parameters
    ----------

    base : int

    n : int
        the number of label dimensions to create

    repeats : int, optional
        the number of repetition for each item. Repeated items have
        distinct names but share the same label. No repetition by
        default.

    name : str, optional
        the name of the file to write. If no name is given (by
        default), no file is written.

    Return
    ------

    A numpy str array containing the generated items
    """

    # Allocate the data matrix
    n_items = (base ** n) * (repeats + 1)
    res = np.empty((n_items + 1, n + 4), dtype='|S6')

    # Fill the header line
    res[0, 0] = '#file'
    res[0, 1] = 'onset'
    res[0, 2] = 'offset'
    res[0, 3] = '#item'
    for j, _ in enumerate(res[0, 4:]):
        res[0, j + 4] = 'c' + str(j)

    # Fill the '#file' column
    for i, _ in enumerate(res[1:, 0]):
        res[i + 1, 0] = 's' + str(i)

    # Fill onset and offset columns with 0
    res[1:, 1] = np.zeros(res[1:, 1].shape)
    res[1:, 2] = np.zeros(res[1:, 2].shape)

    # Fill the '#item' column
    for i, _ in enumerate(res[1:, 3]):
        res[i + 1, 3] = 'i' + str(i)

    # Fill the label columns
    aux = res[1:, 4:]
    for (i, j), _ in np.ndenumerate(aux):
        aux[i][j] = 'c' + str(j) + '_v' + str(i / (base ** j) % base)

    # Write to file if required
    if name != '':
        np.savetxt(name, res, delimiter=' ', fmt='%s')

    return res


def feature(n_items, n_feat=2, max_frames=3, name=''):
    """Random feature generator.

    Generate random features for a set of items, given the feature
    vector size and the maximum number of frames in items.

    Parameters
    ----------

    n_items : int
        number of items for which to generate features

    n_feat : int, optional
        dimension of the generated feature vector. Default is n_feat = 2

    max_frame : int, optional
        number of frames for each item is randomly choosen in [1,max_frame]

    name : str, optional
        the name of the file to write. If no name is given (by
        default), no file is written. Write a HDF5 file.

    Return
    ------

    items : list of item names associated with generated features
    times : list of timestamps for each file
    features : list of feature vectors for each file

    We have len(files) == len(times) == len(features) == n_files

    """

    items, times, features = [], [], []
    for i in xrange(n_items):
        n_frames = np.random.randint(max_frames) + 1
        features.append(np.random.randn(n_frames, n_feat))
        times.append(np.linspace(0, 1, n_frames))
        # TODO Naming files by hand is dangerous -> make a link with item() ?
        items.append('s%d' % i)

    # Write to file if required
    if name != '' :
        # h5feature doesn't support rewritting an existing file...
        if os.path.isfile(name): os.remove(name)
        h5features.write(name, 'features', items, times, features)

    return items, times, features


def item_and_feature(base, n, repeats=0, name_item='', n_feat=2,
                     max_frames=3, name_feature=''):
    """Item and feature generator.

    Wrapper around item() and feature() methods
    """
    # TODO dirty code here ! Clean up
    
    items = item(base, n, repeats, name_item)

    n_files = (base ** n) * (repeats + 1)
    items_name, times, features = feature(n_files, n_feat, max_frames, name_feature)

    return items, items_name, times, features


# # TODO merge item() and item_minimal()
# def item_minimal(base, n, repeats=0, name=''):
#     """Minimal item data generator.

#     Parameters
#     ----------

#     base : int

#     n : int
#         the number of label dimensions to create

#     repeats : int, optional
#         the number of repetition for each item. Repeated items have
#         distinct names but share the same label. No repetition by
#         default.

#     name : str, optional
#         the name of the file to write. If no name is given (by
#         default), no file is written.

#     Return
#     ------

#     A numpy str array containing the generated items
#     """

#     # Allocate the data matrix
#     n_items = (base ** n) * (repeats + 1)
#     res = np.empty((n_items + 1, n + 2), dtype='|S5')

#     # Fill the header line
#     res[0, 0] = '#item'
#     res[0, 1] = '#src'
#     for j, _ in enumerate(res[0, 2:]):
#         res[0, j + 2] = 'c' + str(j)

#     # Fill the '#item' column
#     for i, _ in enumerate(res[1:, 0]):
#         res[i + 1, 0] = 's' + str(i)

#     # Fill the '#src' column
#     for i, _ in enumerate(res[1:, 1]):
#         res[i + 1, 1] = 'i' + str(i)

#     # Fill the label columns
#     aux = res[1:, 2:]
#     for (i, j), _ in np.ndenumerate(aux):
#         aux[i][j] = (i / (base ** j) % base)

#     # Write to file if required
#     if name != '':
#         np.savetxt(name, res, delimiter=' ', fmt='%s')

#     return res
