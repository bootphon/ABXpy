# -*- coding: utf-8 -*-

import ABXpy.task
import os
import h5py
import numpy as np
import items
import pytest



def tables_equivalent(t1, t2):
    assert t1.shape == t2.shape
#    return np.array_equal(t1.sort(), t2.sort()) # faster if the sort for datasets is equivalent
    for a1 in t1:
        res = False
        for a2 in t2:
            if np.array_equal(a1, a2):
                res = True
        if not res:
            return False
    return True

#a = array([array([1,2,3]), array([4,5,6])])
#print a
#print tables_equivalent(a, a)

# test1, full triplet verification
def test_basic():
    items.generate_testitems(2,3,name='data.item')
    try:
        task = ABXpy.task.Task('data.item', 'c0', 'c1', 'c2', filters=None, regressors=None)
        stats = task.stats
        print stats
        assert stats['nb_blocks'] == 8
        assert stats['nb_triplets'] == 8
        assert stats['nb_by_levels'] == 2
        task.generate_triplets()
        f = h5py.File('data.abx', 'r')
        triplets_block0 = f.get('triplets/0')
        triplets_block1 = f.get('triplets/1')
        triplets = np.array([[0,1,2], [1,0,3], [2,3,0], [3,2,1]])
        assert tables_equivalent(triplets, triplets_block0)
        assert tables_equivalent(triplets, triplets_block1)
        pairs = [2,6,7,3,8,12,13,9]
        pairs_block0 = f.get('unique_pairs/0')
        pairs_block1 = f.get('unique_pairs/1')
        assert (set(pairs) == set(pairs_block0[:,0]))
        assert (set(pairs) == set(pairs_block1[:,0]))
    except Exception as error:
        pytest.fail("Could not execute task code: " + error.message)
    finally:
        try:
            os.remove('data.abx')
        except:
            pass
#        pass
        
        
test_basic()