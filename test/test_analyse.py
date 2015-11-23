"""This test script contains tests for analyze.py"""
# -*- coding: utf-8 -*-

import os
import numpy as np

import ABXpy.task
import ABXpy.distances.distances as distances
import ABXpy.distances.metrics.cosine as cosine
import ABXpy.distances.metrics.dtw as dtw
import ABXpy.score as score
import ABXpy.analyze as analyze

from aux import generate
from aux import compare
from aux.frozen import frozen_file


def dtw_cosine_distance(x, y):
    return dtw.dtw(x, y, cosine.cosine_distance)


class TestAnalyze():
    def setup(self):
        self.root = 'test_items'
        if not os.path.exists(self.root):
            os.makedirs(self.root)

        self.files = {}
        for f in ['item', 'feature', 'distance', 'score']:
            self.files[f] = os.path.join(self.root, 'data.' + f)
        self.files['task'] = os.path.join(self.root, 'data.abx')
        self.files['analyze'] = os.path.join(self.root, 'data.csv')
        self.teardown()

        generate.items_and_features(3, 3, 1, self.files['item'],
                                    2, 3, self.files['feature'])
        self.task = ABXpy.task.Task(self.files['item'], 'c0', 'c1', 'c2')

    def teardown(self):
        try:
            for f in self.files.values():
                os.remove(f)
            os.rmdir(self.root)
        except:
            pass

    def test_threshold_analyze(self):
        threshold = 2
        f = self.files

        self.task.generate_triplets(f['task'], threshold=threshold)
        distances.compute_distances(f['feature'], '/features/',
                                    f['task'], f['distance'],
                                    dtw_cosine_distance, n_cpu=1)
        score.score(
            f['task'], f['distance'], f['score'])
        analyze.analyze(
            f['task'], f['score'], f['analyze'])
        number_triplets = np.loadtxt(f['analyze'], dtype=int,
                                     delimiter='\t', skiprows=1, usecols=[-1])
        assert np.all(number_triplets == threshold)

    def test_frozen_analyze(self):
        """Frozen analyze compare the results of a previously "frozen" run with
        a new one, asserting that the code did not change in behaviour.
        """
        f = self.files

        self.task.generate_triplets(f['task'])
        distances.compute_distances(f['feature'], '/features/',
                                    f['task'], f['distance'],
                                    dtw_cosine_distance, n_cpu=1)
        score.score(
            f['task'], f['distance'], f['score'])
        analyze.analyze(
            f['task'], f['score'], f['analyze'])

        # assert compare.h5cmp(f['task'], frozen_file('abx'))
        # assert compare.h5cmp(f['distance'], frozen_file('distance'))
        # assert compare.h5cmp(f['score'], frozen_file('score'))
        assert compare.csvcmp(f['analyze'], frozen_file('csv'))
