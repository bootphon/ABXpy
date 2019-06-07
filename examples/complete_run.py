#!/usr/bin/env python
"""Full run of ABX pipeline with randomly created database and features"""

import os

import ABXpy.task
import ABXpy.distances.distances as distances
import ABXpy.distances.metrics.cosine as cosine
import ABXpy.distances.metrics.dtw as dtw
import ABXpy.score as score
import ABXpy.misc.items as items
import ABXpy.analyze as analyze


def dtw_cosine_distance(x, y, normalized):
    return dtw.dtw(x, y, cosine.cosine_distance, normalized)


def fullrun():
    if not os.path.exists('example_items'):
        os.makedirs('example_items')
    item_file = 'example_items/data.item'
    feature_file = 'example_items/data.features'
    distance_file = 'example_items/data.distance'
    scorefilename = 'example_items/data.score'
    taskfilename = 'example_items/data.abx'
    analyzefilename = 'example_items/data.csv'

    # deleting pre-existing files
    for f in [item_file, feature_file, distance_file,
              scorefilename, taskfilename, analyzefilename]:
        try:
            os.remove(f)
        except OSError:
            pass

    # running the evaluation
    items.generate_db_and_feat(3, 3, 5, item_file, 2, 2, feature_file)

    task = ABXpy.task.Task(item_file, 'c0', across='c1', by='c2')
    task.generate_triplets(taskfilename)

    distances.compute_distances(
        feature_file, 'features', taskfilename,
        distance_file, dtw_cosine_distance,
        normalized=True, n_cpu=1)

    score.score(taskfilename, distance_file, scorefilename)

    analyze.analyze(taskfilename, scorefilename, analyzefilename)


if __name__ == '__main__':
    fullrun()
