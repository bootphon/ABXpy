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
import numpy as np
import items
import random
from scipy.stats import chisquare as chisquare


#FIXME problems when K > N/2 (not important ?)
def chi2test(frequencies, significance):
#    dof = len(frequencies) - 1
    dof = 0
    (_, p) = chisquare(frequencies, ddof=dof)
    return p > significance


def _test_no_replace(N, K):
    """Test the correct functionnality of the sampler, and particularly the no
    replacement property in simple sample"""
    sampler = sampling.sampler.IncrementalSampler(N, K)
    indices = sampler.sample(N)
    indices_test = np.array(list(set(indices)))
    assert len(indices_test) == len(indices)
    assert len(indices) == K


def _test_completion(N, K, n):
    """Test the exact completion of the sample when N is a multiple of N
    """
    sampler = sampling.sampler.IncrementalSampler(N, K)
    count = 0
    for j in range(N/n):
        indices = sampler.sample(n)
        count += len(indices)
    indices = sampler.sample(N % n)
    count += len(indices)
    assert count == K


# this function is really not optimised
def _test_uniformity(N, K, n, nbins=10, significance=0.001):
    """Test the uniformity of a sample

    .. note:: This test is not exact and may return false even if the function
    is correct. Use the significance wisely.

    Parameters:
    -----------
    nbins : int
        the number of bins for the Chi2 test
    """
    sampler = sampling.sampler.IncrementalSampler(N, K)
    distr = []
    bins = np.zeros(nbins, np.int64)
    for j in range(N/n):
        indices = sampler.sample(n) + n*j
        distr.extend(indices.tolist())
    for i in distr:
        bins[i * nbins / N] += 1
    assert chi2test(bins, significance)


def test_simple_completion():
    for i in range(1000):
        N = random.randint(1000, 10000)
        _test_completion(N, K=random.randrange(100, N/2),
                         n=random.randrange(50, N))


def test_simple_no_replace():
    for i in range(100):
        N = random.randint(1000, 10000)
        _test_no_replace(N, random.randint(100, N/2))


def test_hard_completion():
    for i in range(3):
        N = random.randint(10**6, 10**7)
        _test_completion(N, K=random.randrange(10**5, N/2),
                         n=random.randrange(10**5, N))


def test_hard_no_replace():
    for i in range(3):
        N = random.randint(10**6, 10**7)
        _test_no_replace(N, K=random.randrange(10**5, N/2))


def test_simple_uniformity():
    for i in range(100):
        N = random.randint(1000, 10000)
        _test_completion(N, K=random.randrange(100, N/2),
                         n=random.randrange(50, N))


def test_sampling_task():
    items.generate_testitems(4, 6, name='data.item')
    try:
        task = ABXpy.task.Task('data.item', 'c0', 'c1', ['c2', 'c3'],
                               verify=False)
        print "stats computed"
        # stats = task.stats
        task.generate_triplets(sample=0.2)
        print "first sample"
        os.remove('data.abx')
        task.generate_triplets(sample=200)
        print "second sample"
    finally:
        try:
            os.remove('data.abx')
            os.remove('data.item')
        except:
            pass


import matplotlib.pyplot as plt


def plot_uniformity(nb_resamples, N, K):
    indices = []
    for i in range(nb_resamples):
        if i % 1000 == 0:
            print('%d resamples left to do' % (nb_resamples-i))
        sampler = sampling.sampler.IncrementalSampler(N, K)
        current_N = 0
        while current_N < N:
            n = min(random.randrange(N/10), N-current_N)
            indices = indices + list(sampler.sample(n) + current_N)
            current_N = current_N + n
    plt.hist(indices, bins=100)


# test_simple_uniformity()
# test_hard_completion()
# test_hard_no_replace()
# test_simple_no_replace()
# test_simple_completion()
# plot_uniformity(10**4, 10**3, 10)
