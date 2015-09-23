"""This test script contains tests for the basic parameters of task.py
"""
# -*- coding: utf-8 -*-

import os
import sys
import h5py
import numpy as np

import ABXpy.task
import ABXpy.misc.items as items

error_pairs = "pairs incorrectly generated"
error_triplets = "triplets incorrectly generated"


# not optimized, but unimportant
def tables_equivalent(t1, t2):
    assert t1.shape == t2.shape
    for a1 in t1:
        res = False
        for a2 in t2:
            if np.array_equal(a1, a2):
                res = True
        if not res:
            return False
    return True


# test1, triplets and pairs verification
def test_basic():
    items.generate_testitems(2, 3, name='data.item')
    try:
        task = ABXpy.task.Task('data.item', 'c0', 'c1', 'c2')
        stats = task.stats
        assert stats['nb_blocks'] == 8, "incorrect stats: number of blocks"
        assert stats['nb_triplets'] == 8
        assert stats['nb_by_levels'] == 2
        task.generate_triplets()
        f = h5py.File('data.abx', 'r')
        triplets_block0 = f.get('triplets/0')
        triplets_block1 = f.get('triplets/1')
        triplets = np.array([[0, 1, 2], [1, 0, 3], [2, 3, 0], [3, 2, 1]])
        assert tables_equivalent(triplets, triplets_block0), error_triplets
        assert tables_equivalent(triplets, triplets_block1), error_triplets
        pairs = [2, 6, 7, 3, 8, 12, 13, 9]
        pairs_block0 = f.get('unique_pairs/0')
        pairs_block1 = f.get('unique_pairs/1')
        assert (set(pairs) == set(pairs_block0[:, 0])), error_pairs
        assert (set(pairs) == set(pairs_block1[:, 0])), error_pairs
    finally:
        try:
            os.remove('data.abx')
            os.remove('data.item')
        except:
            pass


# testing with a list of across attributes, triplets verification
def test_multiple_across():
    items.generate_testitems(2, 3, name='data.item')
    try:
        task = ABXpy.task.Task('data.item', 'c0', ['c1', 'c2'])
        stats = task.stats
        assert stats['nb_blocks'] == 8
        assert stats['nb_triplets'] == 8
        assert stats['nb_by_levels'] == 1
        task.generate_triplets()
        f = h5py.File('data.abx', 'r')
        triplets_block = f.get('triplets/0')
        triplets = np.array([[0, 1, 6], [1, 0, 7], [2, 3, 4], [3, 2, 5],
                             [4, 5, 2], [5, 4, 3], [6, 7, 0], [7, 6, 1]])
        assert tables_equivalent(triplets, triplets_block)
    finally:
        try:
            os.remove('data.abx')
            os.remove('data.item')
        except:
            pass


# testing without any across attribute
def test_no_across():
    items.generate_testitems(2, 3, name='data.item')
    try:
        task = ABXpy.task.Task('data.item', 'c0', None, 'c2')
        stats = task.stats
        assert stats['nb_blocks'] == 8
        assert stats['nb_triplets'] == 16
        assert stats['nb_by_levels'] == 2
        task.generate_triplets()
    finally:
        try:
            os.remove('data.abx')
            os.remove('data.item')
        except:
            pass


# testing for multiple by attributes, asserting the statistics
def test_multiple_bys():
    items.generate_testitems(3, 4, name='data.item')
    try:
        task = ABXpy.task.Task('data.item', 'c0', None, ['c1', 'c2', 'c3'])
        stats = task.stats
        assert stats['nb_blocks'] == 81
        assert stats['nb_triplets'] == 0
        assert stats['nb_by_levels'] == 27
        task.generate_triplets()
    finally:
        try:
            os.remove('data.abx')
            os.remove('data.item')
        except:
            pass


# testing for a general filter (discarding last column)
def test_filter():
    items.generate_testitems(2, 4, name='data.item')
    try:
        task = ABXpy.task.Task('data.item', 'c0', 'c1', 'c2',
                               filters=["[attr == 0 for attr in c3]"])
        stats = task.stats
        assert stats['nb_blocks'] == 8, "incorrect stats: number of blocks"
        assert stats['nb_triplets'] == 8
        assert stats['nb_by_levels'] == 2
        task.generate_triplets()
        f = h5py.File('data.abx', 'r')
        triplets_block0 = f.get('triplets/0')
        triplets_block1 = f.get('triplets/1')
        triplets = np.array([[0, 1, 2], [1, 0, 3], [2, 3, 0], [3, 2, 1]])
        assert tables_equivalent(triplets, triplets_block0), error_triplets
        assert tables_equivalent(triplets, triplets_block1), error_triplets
        pairs = [2, 6, 7, 3, 8, 12, 13, 9]
        pairs_block0 = f.get('unique_pairs/0')
        pairs_block1 = f.get('unique_pairs/1')
        assert (set(pairs) == set(pairs_block0[:, 0])), error_pairs
        assert (set(pairs) == set(pairs_block1[:, 0])), error_pairs
    finally:
        try:
            os.remove('data.abx')
            os.remove('data.item')
        except:
            pass


# testing with simple filter on A, verifying triplet generation
def test_filter_on_A():
    items.generate_testitems(2, 2, name='data.item')
    try:
        task = ABXpy.task.Task('data.item', 'c0',
                               filters=["[attr == 0 for attr in c0_A]"])
        stats = task.stats
        assert stats['nb_blocks'] == 4, "incorrect stats: number of blocks"
        assert stats['nb_triplets'] == 4
        assert stats['nb_by_levels'] == 1
        task.generate_triplets()
        f = h5py.File('data.abx', 'r')
        triplets_block0 = f.get('triplets/0')
        triplets = np.array([[0, 1, 2], [0, 3, 2], [2, 1, 0], [2, 3, 0]])
        assert tables_equivalent(triplets, triplets_block0), error_triplets
    finally:
        try:
            os.remove('data.abx')
            os.remove('data.item')
        except:
            pass


# testing with simple filter on B, verifying triplet generation
def test_filter_on_B():
    items.generate_testitems(2, 2, name='data.item')
    try:
        task = ABXpy.task.Task('data.item', 'c0',
                               filters=["[attr == 0 for attr in c1_B]"])
        stats = task.stats
        assert stats['nb_blocks'] == 4, "incorrect stats: number of blocks"
        assert stats['nb_triplets'] == 4
        assert stats['nb_by_levels'] == 1
        task.generate_triplets()
        f = h5py.File('data.abx', 'r')
        triplets_block0 = f.get('triplets/0')
        triplets = np.array([[0, 1, 2], [1, 0, 3], [2, 1, 0], [3, 0, 1]])
        assert tables_equivalent(triplets, triplets_block0), error_triplets
    finally:
        try:
            os.remove('data.abx')
            os.remove('data.item')
        except:
            pass


# testing with simple filter on C, verifying triplet generation
def test_filter_on_C():
    items.generate_testitems(2, 2, name='data.item')
    try:
        task = ABXpy.task.Task('data.item',
                               'c0',
                               filters=["[attr == 0 for attr in c1_X]"])
        stats = task.stats
        assert stats['nb_blocks'] == 4, "incorrect stats: number of blocks"
        assert stats['nb_triplets'] == 4
        assert stats['nb_by_levels'] == 1
        task.generate_triplets()
        f = h5py.File('data.abx', 'r')
        triplets_block0 = f.get('triplets/0')
        triplets = np.array([[2, 1, 0], [2, 3, 0], [3, 0, 1], [3, 2, 1]])
        assert tables_equivalent(triplets, triplets_block0), error_triplets
    finally:
        try:
            os.remove('data.abx')
            os.remove('data.item')
        except:
            pass

def test_task_parser():
    """Test case for the task_parser() method"""
    
    by1 = ABXpy.task.task_parser('db -o c0 -b c0 -b c1').by
    by2 = ABXpy.task.task_parser('db -o c0 -b c0 c1').by
    assert by1 == by2 == ['c0', 'c1']

    ac1 = ABXpy.task.task_parser('db -o c0 -a c0 -a c1 -a c2').across
    ac2 = ABXpy.task.task_parser('db -o c0 -a c0 c1 c2').across
    ac3 = ABXpy.task.task_parser('db -o c0 -a c0 c1 -a c2').across
    assert ac1 == ac2 == ac3 == ['c0', 'c1', 'c2']

def main():
    # test_basic()
    # test_multiple_across()
    # test_no_across()
    # test_multiple_bys()
    # test_filter()
    # test_filter_on_C()
    test_task_parser()

if __name__ == '__main__':
    main()

