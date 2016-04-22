"""This test contains a full run of the ABX pipeline with randomly created
database and features
"""
# -*- coding: utf-8 -*-

import os
import sys
package_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if not(package_path in sys.path):
    sys.path.append(package_path)
import ABXpy.task
import ABXpy.distances.distances as distances
import ABXpy.distances.metrics.cosine as cosine
import ABXpy.distances.metrics.dtw as dtw
import ABXpy.score as score
import ABXpy.misc.items as items
import ABXpy.analyze as analyze


def dtw_cosine_distance(x, y):
    return dtw.dtw(x, y, cosine.cosine_distance)


def fullrun():
    if not os.path.exists('example_items'):
        os.makedirs('example_items')
    item_file = 'example_items/data.item'
    feature_file = 'example_items/data.features'
    distance_file = 'example_items/data.distance'
    scorefilename = 'example_items/data.score'
    taskfilename = 'example_items/data.abx'
    analyzefilename = 'example_items/data.csv'

    items.generate_db_and_feat(3, 3, 1, item_file, 2, 2, feature_file)
    task = ABXpy.task.Task(item_file, 'c0', across='c1', by='c2')
    task.generate_triplets(taskfilename)
    distances.compute_distances(feature_file, '/features/', taskfilename,
                                distance_file, dtw_cosine_distance, n_cpu=1)
    score.score(taskfilename, distance_file, scorefilename)
    analyze.analyze(taskfilename, scorefilename, analyzefilename)


fullrun()
