"""This script is used to verify the consistency of your input files.

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

import argparse


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
    with open(filename) as f:
        cols = str.split(f.readline())
        assert len(cols) >= 4, 'the syntax of the item file is incorrect'
        assert cols[0] == '#file', 'The first column must be named #file'
        assert cols[1] == 'onset', 'The second column must be named onset'
        assert cols[2] == 'offset', 'The third column must be named offset'
        assert cols[3][0] == '#', 'The fourth column must start with #'
        if verbose:
            print("Opening features file")
        h5f = h5py.File(features)
        files = h5f['features']['files'][:]
        for line in f:
            source = str.split(line, ' ')[0]
            assert source in files, ("The file {} cannot "
                                     "be found in the feature file"
                                     .format(source))


def parse_args():
    parser = argparse.ArgumentParser(
        prog='collapse_results.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Collapse results of ABX on by conditions.',
        epilog="""Example usage:

$ ./verify.py my_data.item my_features.h5f

verify the consistency between the item file and the features file""")
    parser.add_argument('item', metavar='ITEM_FILE',
                        help='database description file in .item format')
    parser.add_argument('features', metavar='FEATURES_FILE',
                        help='features file in h5features format')
    return vars(parser.parse_args())


if __name__ == '__main__':
    args = parse_args()
    check(args['item'], args['features'])
