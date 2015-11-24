"""This test script contains tests for the basic parameters of score.py"""

import os

import ABXpy.task
import ABXpy.score as score
import ABXpy.distances.distances as distances
from ABXpy.distances.example_distances import dtw_cosine

import aux.generate as generate


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

    # TODO This is too long for testing, reduce computation
    # def test_score(self):
    #     generate.items_and_features(2, 3, 1, self.files['item'],
    #                                 1, 1, self.files['feature'])

    #     task = ABXpy.task.Task(self.files['item'], 'c0', 'c1', 'c2')
    #     task.generate_triplets()

    #     distances.compute_distances(
    #         self.files['feature'], '/features/', self.files['task'],
    #         self.files['distance'], dtw_cosine, n_cpu=3)

    #     score.score(
    #         self.files['task'], self.files['distance'], self.files['score'])
