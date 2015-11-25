"""Verifies the consistency of item and features files.

Usage
-----

From the command line:

.. code-block:: bash

    python verify.py my_data.item my_features.h5f

In python:

.. code-block:: python

    import ABXpy.verify
    # create a new task and compute the statistics
    ABXpy.verify.check('my_data.item', 'my_data.h5f')
"""

import h5py


def check(item_file, features_file, verbose=0):
    """check the consistency between the item file and the features file

    Parameters:
    item_file: str
        the item file defining the database
    features_file : str
        the features file to be tested
    """
    if verbose:
        print("Opening item file")
    with open(item_file) as f:
        cols = str.split(f.readline())
        assert len(cols) >= 4, 'the syntax of the item file is incorrect'
        assert cols[0] == '#file', 'The first column must be named #file'
        assert cols[1] == 'onset', 'The second column must be named onset'
        assert cols[2] == 'offset', 'The third column must be named offset'
        assert cols[3][0] == '#', 'The fourth column must start with #'
        if verbose:
            print("Opening features file")
        h5f = h5py.File(features_file)
        files = h5f['features']['files'][:]
        for line in f:
            source = str.split(line, ' ')[0]
            assert source in files, ("The file {} cannot "
                                     "be found in the feature file"
                                     .format(source))
