"""This test script contains tests for the basic parameters of score.py"""

import os
import shutil

import ABXpy.task
import ABXpy.distances.distances as distances
import ABXpy.distances.metrics.cosine as cosine
import ABXpy.distances.metrics.dtw as dtw
import ABXpy.score as score
import ABXpy.misc.items as items


def dtw_cosine_distance(x, y, normalized):
    return dtw.dtw(x, y, cosine.cosine_distance, normalized)


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
            distance_file, dtw_cosine_distance,
            normalized=True, n_cpu=3)
        score.score(taskfilename, distance_file, scorefilename)
    finally:
        shutil.rmtree('test_items', ignore_errors=True)
