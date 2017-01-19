"""This test script contains tests for the basic parameters of score.py
"""
# -*- coding: utf-8 -*-

import os
import shutil
import sys

package_path = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))))
if not(package_path in sys.path):
    sys.path.append(package_path)
import ABXpy.task
import ABXpy.distances.distances as distances
import ABXpy.distances.metrics.cosine as cosine
import ABXpy.distances.metrics.dtw as dtw
import ABXpy.score as score
import ABXpy.misc.items as items


def dtw_cosine_distance(x, y):
    return dtw.dtw(x, y, cosine.cosine_distance)


def test_score():
    try:
        if not os.path.exists('test_items'):
            os.makedirs('test_items')
        item_file = 'test_items/data.item'
        feature_file = 'test_items/data.features'
        distance_file = 'test_items/data.distance'
        scorefilename = 'test_items/data.score'
        taskfilename = 'test_items/data.abx'
        items.generate_db_and_feat(3, 3, 1, item_file, 2, 3, feature_file)
        task = ABXpy.task.Task(item_file, 'c0', 'c1', 'c2')
        task.generate_triplets()
        distances.compute_distances(
            feature_file, '/features/', taskfilename,
            distance_file, dtw_cosine_distance, n_cpu=3)
        score.score(taskfilename, distance_file, scorefilename)
    finally:
        try:
            shutil.rmtree('test_items')
            # os.remove(item_file)
            # os.remove(feature_file)
            # os.remove(taskfilename)
            # os.remove(distance_file)
            # os.remove(scorefilename)
        except:
            pass
