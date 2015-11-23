"""This test script contains tests for the basic parameters of score.py"""

import os
import sys

import ABXpy.task
import ABXpy.distances.distances as distances
import ABXpy.distances.metrics.cosine as cosine
import ABXpy.distances.metrics.dtw as dtw
import ABXpy.score as score
import ABXpy.misc.items as items


def dtw_cosine_distance(x, y):
    return dtw.dtw(x, y, cosine.cosine_distance)


class TestScore:
    def setup(self):
        self.root = 'test_items'
        if not os.path.exists(self.root):
            os.makedirs(self.root)

        self.files = {}
        for f in ['item', 'feature', 'distance', 'score']:
            self.files[f] = os.path.join(self.root, 'data.' + f)
        self.files['task'] = os.path.join(self.root, 'data.abx')

        self.teardown()

    def teardown(self):
        try:
            for f in self.files.values():
                os.remove(f)
            os.rmdir(self.root)
        except:
            pass

    def test_score(self):
        items.generate_db_and_feat(
            3, 3, 1, self.files['item'], 2, 3, self.files['feature'])

        task = ABXpy.task.Task(self.files['item'], 'c0', 'c1', 'c2')
        task.generate_triplets()

        distances.compute_distances(
            self.files['feature'], '/features/', self.files['task'],
            self.files['distance'], dtw_cosine_distance, n_cpu=3)

        score.score(
            self.files['task'], self.files['distance'], self.files['score'])
