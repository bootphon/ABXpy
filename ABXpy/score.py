"""This module is used for computing the score of a task (see `task Module`_ on
how to create a task)

This module contains the actual computation of the score. It requires a task
and a distance, and redirect the output in a score file.

The main function takes a distance file and a task file as input to compute
the score of the task on those distances. X closer to A is associated with
a score of 1 and X closer to B with  score of -1.

The distances between pairs in the distance file must be ordered the same
way as the pairs in the task file, and the triplet score int the output
file will be ordered the same way as the triplets in the task file.

Usage
-----
Form the command line:

.. code-block:: bash

    python score.py data.abx data.distance data.score

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

import os
import h5py
import numpy as np

import ABXpy.h5tools.h52np as h52np
# import ABXpy.h5tools.np2h5 as np2h5
import ABXpy.misc.type_fitting as type_fitting


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
    # with h5py.File(task_file) as t:
    #     bys = [by for by in t['triplets']]
    # FIXME skip empty by datasets, this should not be necessary anymore when
    # empty datasets are filtered at the task file generation level
    with h5py.File(task_file) as t:
        bys = t['bys'][...]
        # bys = t['feat_dbs'].keys()
        n_triplets = t['triplets']['data'].shape[0]
    with h5py.File(score_file) as s:
        s.create_dataset('scores', (n_triplets, 1), dtype=np.int8)
        for n_by, by in enumerate(bys):
            with h5py.File(task_file) as t, h5py.File(distance_file) as d:
                trip_attrs = t['triplets']['by_index'][n_by]
                pair_attrs = t['unique_pairs'].attrs[by]
                # FIXME here we make the assumption
                # that this fits into memory ...
                dis = d['distances']['data'][pair_attrs[1]:pair_attrs[2]][...]
                dis = np.reshape(dis, dis.shape[0])
                # FIXME idem + only unique_pairs used ?
                pairs = t['unique_pairs']['data'][pair_attrs[1]:pair_attrs[2]][...]
                pairs = np.reshape(pairs, pairs.shape[0])
                base = pair_attrs[0]
                pair_key_type = type_fitting.fit_integer_type((base) ** 2 - 1,
                                                              is_signed=False)
            with h52np.H52NP(task_file) as t:
                inp = t.add_subdataset('triplets', 'data', indexes=trip_attrs)
                idx_start = trip_attrs[0]
                for triplets in inp:
                    triplets = pair_key_type(triplets)
                    idx_end = idx_start + triplets.shape[0]

                    pairs_AX = triplets[:, 0] + base * triplets[:, 2]
                    # FIXME change the encoding (and type_fitting) so that
                    # A,B and B,A have the same code ... (take a=min(a,b),
                    # b=max(a,b))
                    pairs_BX = triplets[:, 1] + base * triplets[:, 2]
                    dis_AX = dis[np.searchsorted(pairs, pairs_AX)]

                    dis_BX = dis[np.searchsorted(pairs, pairs_BX)]
                    scores = (np.int8(dis_AX < dis_BX) -
                              np.int8(dis_AX > dis_BX))
                    # 1 if X closer to A, -1 if X closer to B, 0 if equal
                    # distance (this doesn't use 0, 1/2, 1 to use the
                    # compact np.int8 data format)
                    s['scores'][idx_start:idx_end] = np.reshape(scores,
                                                                (-1, 1))
                    idx_start = idx_end
