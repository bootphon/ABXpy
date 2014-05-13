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
import random

#TODO test rejection sampling
#FIXME sampling without replacement does not work for K > 10^5
#FIXME problems when K > N/2 (not important ?)


def test_no_replace(N, K):
    """Test the correct functionnality of the sampler, and particularly the no
    replacement property in simple sample"""
    sampler = sampling.sampler.IncrementalSampler(N, K)
    indices = sampler.sample(N)
    indices_test = np.array(list(set(indices)))
    assert len(indices_test) == len(indices)
    assert len(indices) == K


def test_completion(N, K, n):
    """Test the exact completion of the sample when N is a multiple of N
    """
    sampler = sampling.sampler.IncrementalSampler(N, K)
    count = 0
    for j in range(N/n):
        indices = sampler.sample(n)
        count += len(indices)
    assert (count <= K + (N % n)) & (count >= K - (N % n))


def test_simple_completion():
    for i in range(1000):
        N = random.randint(1000, 10000)
        test_completion(N, K=random.randrange(100, N/2),
                        n=random.randrange(50, N))


def test_simple_no_replace():
    for i in range(100):
        N = random.randint(1000, 10000)
        test_no_replace(N, random.randint(100, N/2))


def test_hard_completion():
    for i in range(5):
        N = random.randint(10**6, 10**7)
        test_completion(N, K=random.randrange(10**5, N/2),
                        n=random.randrange(10**5, N))


def test_hard_no_replace():
    for i in range(5):
        N = random.randint(10**6, 10**7)
        test_no_replace(N, K=random.randrange(10**5, N/2))

test_hard_completion()
#test_hard_no_replace()  #wont work for now
test_simple_no_replace()
test_simple_completion()
