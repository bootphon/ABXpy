"""This module is used for computing the score of a task (see `task Module`_ on
how to create a task)

This module contains the actual computation of the score. It requires a task
and a distance, and redirect the output in a score file.

Usage
-----
Form the command line:

.. code-block:: bash

    Not implemented yet.

In python:

.. code-block:: python

    import ABXpy.task
    import ABXpy.score
    # create a new task:
    myTask = ABXpy.task.Task('data.item', 'on_feature', 'across_feature', \
'by_feature', filters=my_filters, regressors=my_regressors)
    myTask.generate_triplets()
    #initialise distance
    #TODO shouldn't this be available from score
    # calculate the scores:
    ABXpy.score('data.abx', 'myDistance.???', 'data.score')
"""
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 12:28:05 2013

@author: Thomas Schatz
"""

# make sure the rest of the ABXpy package is accessible
import os
import sys
package_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if not(package_path in sys.path):
    sys.path.append(package_path)

import h5py
import numpy as np
import ABXpy.h5tools.h52np as h52np
import ABXpy.h5tools.np2h5 as np2h5
import ABXpy.misc.type_fitting as type_fitting


#FIXME: include distance computation here
def score(task_file, distance_file, score_file=None, score_group='scores'):
    """Calculate the score of a task and put the results in a hdf5 file.

    Parameters
    ----------
    task_file : string
        The hdf5 file containing the task (with the triplets and pairs
        generated)
    distance_file : string
        The hdf5 file containing the distances between the pairs
    score_file : string, optional
        The hdf5 file that will contain the results
    """
    if score_file is None:
        (basename_task, _) = os.path.splitext(task_file)
        (basename_dist, _) = os.path.splitext(distance_file)
        score_file = basename_task + '_' + basename_dist + '.score'
    # file verification:
    assert os.path.exists(task_file), 'Cannot find task file ' + task_file
    assert os.path.exists(distance_file), ('Cannot find distance file ' +
                                           distance_file)
    assert not os.path.exists(score_file), ('score file already exist ' +
                                            score_file)
    #with h5py.File(task_file) as t:
        #bys = [by for by in t['triplets']]
    #FIXME skip empty by datasets, this should not be necessary anymore when
    # empty datasets are filtered at the task file generation level
    with h5py.File(distance_file) as d:
        bys = [by for by in d['distances']]
    for by in bys:
        with h5py.File(task_file) as t, h5py.File(distance_file) as d:
            n = t['triplets'][by].shape[0]
            #FIXME here we make the assumption
            # that this fits into memory ...
            dis = d['distances'][by][...]
            dis = np.reshape(dis, dis.shape[0])
            #FIXME idem + only unique_pairs used ?
            pairs = t['unique_pairs'][by][...]
            pairs = np.reshape(pairs, pairs.shape[0])
            base = t['unique_pairs'].attrs[by]
            pair_key_type = type_fitting.fit_integer_type((base)**2-1,
                                                          is_signed=False)
        with h52np.H52NP(task_file) as t:
            with np2h5.NP2H5(score_file) as s:
                inp = t.add_dataset('triplets', by)
                out = s.add_dataset('scores', by, n_rows=n, n_columns=1,
                                    item_type=np.int8)
                try:  # FIXME replace this by a for loop by making h52np
                # implement the iterable pattern with next() outputing
                # inp.read()
                    while True:  # FIXME keep the pairs in the file ?
                        triplets = pair_key_type(inp.read())
                        pairs_AX = triplets[:, 0]+base*triplets[:, 2]
                        #FIXME change the encoding (and type_fitting) so that
                        # A,B and B,A have the same code ... (take a=min(a,b),
                        # b=max(a,b))
                        pairs_BX = triplets[:, 1]+base*triplets[:, 2]
                        dis_AX = dis[np.searchsorted(pairs, pairs_AX)]
                        dis_BX = dis[np.searchsorted(pairs, pairs_BX)]
                        scores = (np.int8(dis_AX < dis_BX) -
                                  np.int8(dis_AX > dis_BX))
                        # 1 if X closer to A, -1 if X closer to B, 0 if equal
                        # distance (this doesn't use 0, 1/2, 1 to use the
                        # compact np.int8 data format)
                        out.write(np.reshape(scores, (scores.shape[0], 1)))
                except StopIteration:
                    pass

#FIXME write command-line interface
# detects whether the script was called from command-line
if __name__ == '__main__':

    import argparse

    # parser (the usage string is specified explicitly because the default
    # does not show that the mandatory arguments must come before the mandatory
    # ones; otherwise parsing is not possible beacause optional arguments can
    # have various numbers of inputs)
    parser = argparse.ArgumentParser(usage="%(prog)s task distance [score]",
                                     description='ABX score computation')
    # I/O files
    g1 = parser.add_argument_group('I/O files')
    g1.add_argument('task', help='task file generated by the task module, \
        containing the triplets and the pairs associated to the task \
        specification')
    g1.add_argument('distance', help='distance file generated by the distance \
        package, containing the distance between the pairs of a task')
    g1.add_argument('score', nargs='?', default=None, help='optional: score \
        file, where the results of the computation will be put')
    args = parser.parse_args()
    score(args.task, args.distance, args.score)
"""This module is used for computing the score of a task (see `task Module`_ on
how to create a task) according to a distance (see `distance Module`_)

This module contains the actual computation of the score. It requires a task
and a distance file, and redirect the output in a score file.

Usage
-----
Form the command line:

.. code-block:: bash

    python score.py data.abx data.distance data.score

In python:

.. code-block:: python

    import ABXpy.score
    # calculate the scores:
    ABXpy.score('data.abx', 'data.distance', 'data.score')
"""
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 12:28:05 2013

@author: Thomas Schatz
"""

# make sure the rest of the ABXpy package is accessible
import os
import sys
package_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if not(package_path in sys.path):
    sys.path.append(package_path)

import h5py
import numpy as np
import ABXpy.h5tools.h52np as h52np
import ABXpy.h5tools.np2h5 as np2h5
import ABXpy.misc.type_fitting as type_fitting


#FIXME: include distance computation here
def score(task_file, distance_file, score_file=None, score_group='scores'):
    """Calculate the score of a task and put the results in a hdf5 file.

    Parameters
    ----------
    task_file : string
        The hdf5 file containing the task (with the triplets and pairs
        generated)
    distance_file : string
        The hdf5 file containing the distances between the pairs
    score_file : string, optional
        The hdf5 file that will contain the results
    """
    if score_file is None:
        (basename_task, _) = os.path.splitext(task_file)
        (basename_dist, _) = os.path.splitext(distance_file)
        score_file = basename_task + '_' + basename_dist + '.score'
    # file verification:
    assert os.path.exists(task_file), 'Cannot find task file ' + task_file
    assert os.path.exists(distance_file), ('Cannot find distance file ' +
                                           distance_file)
    assert not os.path.exists(score_file), ('score file already exist ' +
                                            score_file)
    #with h5py.File(task_file) as t:
        #bys = [by for by in t['triplets']]
    #FIXME skip empty by datasets, this should not be necessary anymore when
    # empty datasets are filtered at the task file generation level
    with h5py.File(distance_file) as d:
        bys = [by for by in d['distances']]
    for by in bys:
        with h5py.File(task_file) as t, h5py.File(distance_file) as d:
            n = t['triplets'][by].shape[0]
            #FIXME here we make the assumption
            # that this fits into memory ...
            dis = d['distances'][by][...]
            dis = np.reshape(dis, dis.shape[0])
            #FIXME idem + only unique_pairs used ?
            pairs = t['unique_pairs'][by][...]
            pairs = np.reshape(pairs, pairs.shape[0])
            base = t['unique_pairs'].attrs[by]
            pair_key_type = type_fitting.fit_integer_type((base)**2-1,
                                                          is_signed=False)
        with h52np.H52NP(task_file) as t:
            with np2h5.NP2H5(score_file) as s:
                inp = t.add_dataset('triplets', by)
                out = s.add_dataset('scores', by, n_rows=n, n_columns=1,
                                    item_type=np.int8)
                try:  # FIXME replace this by a for loop by making h52np
                # implement the iterable pattern with next() outputing
                # inp.read()
                    while True:  # FIXME keep the pairs in the file ?
                        triplets = pair_key_type(inp.read())
                        pairs_AX = triplets[:, 0]+base*triplets[:, 2]
                        #FIXME change the encoding (and type_fitting) so that
                        # A,B and B,A have the same code ... (take a=min(a,b),
                        # b=max(a,b))
                        pairs_BX = triplets[:, 1]+base*triplets[:, 2]
                        dis_AX = dis[np.searchsorted(pairs, pairs_AX)]
                        dis_BX = dis[np.searchsorted(pairs, pairs_BX)]
                        scores = (np.int8(dis_AX < dis_BX) -
                                  np.int8(dis_AX > dis_BX))
                        # 1 if X closer to A, -1 if X closer to B, 0 if equal
                        # distance (this doesn't use 0, 1/2, 1 to use the
                        # compact np.int8 data format)
                        out.write(np.reshape(scores, (scores.shape[0], 1)))
                except StopIteration:
                    pass

#FIXME write command-line interface
# detects whether the script was called from command-line
if __name__ == '__main__':

    import argparse

    # parser (the usage string is specified explicitly because the default
    # does not show that the mandatory arguments must come before the mandatory
    # ones; otherwise parsing is not possible beacause optional arguments can
    # have various numbers of inputs)
    parser = argparse.ArgumentParser(usage="%(prog)s task distance [score]",
                                     description='ABX score computation')
    # I/O files
    g1 = parser.add_argument_group('I/O files')
    g1.add_argument('task', help='task file generated by the task module, \
        containing the triplets and the pairs associated to the task \
        specification')
    g1.add_argument('distance', help='distance file generated by the distance \
        package, containing the distance between the pairs of a task')
    g1.add_argument('score', nargs='?', default=None, help='optional: score \
        file, where the results of the computation will be put')
    args = parser.parse_args()
    score(args.task, args.distance, args.score)
