"""This test script contains the tests for the sampling module and its use
with task.py"""
# -*- coding: utf-8 -*-

import os
import sys
package_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if not(package_path in sys.path):
    sys.path.append(package_path)
import ABXpy.task
import ABXpy.sampling as sampling
import h5py
import numpy as np
import items

#TODO test rejection sampling

def test_simple_no_replace(N=1000, K=500):
    """Test the correct functionnality of the sampler, and particularly the no
    replacement property in simple sample"""
    sampler = sampling.sampler.IncrementalSampler(N, K)
    indices = sampler.sample(N)
    indices_test = np.array(list(set(indices)))
    print len(indices_test)
    print len(indices)
    assert len(indices_test) == len(indices)
    assert len(indices) == K


def test_simple_completion(N=1000, K=500, n=100):
    """Test the exact completion of the sample when N is a multiple of N
    """
    sampler = sampling.sampler.IncrementalSampler(N, K)
    count = 0
    for j in range(N/n):
        indices = sampler.sample(n)
        count += len(indices)
    print count
    assert (count <= K + (N % n)) & (count >= K - (N % n))


#FIXME SAMPLER NO REPLACEMENT DOESNT SEEMS TO WORK FOR K > 10^5
for i in range(100):
    test_simple_completion(N=1010, K= 478, n=99)
#test_simple_no_replace(1000000, 300000)
#test_simple_completion(1000000, 200000)
