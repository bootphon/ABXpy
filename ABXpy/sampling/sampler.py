"""The sampler class implementing incremental sampling without replacement.
Incremental meaning that you don't have to draw the whole sample at once,
instead at any given time you can get a piece of the sample of a size you
specify.
This is useful for very large sample sizes.
"""
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 18 03:14:53 2013

@author: Thomas Schatz
"""

import numpy as np
import math


"""Class for sampling without replacement in an incremental fashion

Toy example of usage:
    sampler = IncrementalSampler(10**4, 10**4, step=100, \
relative_indexing=False)
    complete_sample = np.concatenate([sample for sample in sampler])
    assert all(complete_sample==range(10**4))

More realistic example of usage: sampling without replacement 1 million items
from a total of 1 trillion items, considering 100 millions items at a time
    sampler = IncrementalSampler(10**12, 10**6, step=10**8, \
relative_indexing=False)
    complete_sample = np.concatenate([sample for sample in sampler])
"""


class IncrementalSampler(object):

    # sampling K sample in a a population of size N
    # both K and N can be very large

    def __init__(self, N, K, step=None, relative_indexing=True,
                 dtype=np.int64):
        assert K <= N
        self.N = N  # remaining items to sample from
        self.K = K  # remaining items to be sampled
        self.initial_N = N
        self.relative_indexing = relative_indexing
        self.type = dtype  # the type of the elements of the sample
        # step used when iterating over the sampler
        if step is None:
            # 10**4 samples by iteration on average
            self.step = 10 ** 4 * N // K
        else:
            self.step = step

    # method for implementing the iterable pattern
    def __iter__(self):
        return self

    # method for implementing the iterable pattern
    def next(self):
        if self.N == 0:
            raise StopIteration
        return self.sample(self.step)

    def sample(self, n, dtype=np.int64):
        """Fast implementation of the sampling function

        Get all samples from the next n items in a way that avoid rejection
        sampling with too large samples, more precisely samples whose expected
        number of sampled items is larger than 10**5.

        Parameters
        ----------
        n : int
            the size of the chunk
        Returns
        -------
        sample : numpy.array
            the indices to keep given relative to the current position
            in the sample or absolutely, depending on the value of
            relative_indexing specified when initialising the sampler
            (default value is True)
        """
        self.type = dtype
        position = self.initial_N - self.N
        if n > self.N:
            n = self.N
        # expected number of sampled items
        expected_k = n * self.K / np.float(self.N)
        if expected_k > 10 ** 5:
            sample = []
            chunk_size = int(np.floor(10 ** 5 * self.N / np.float(self.K)))
            i = 0
            while n > 0:
                amount = min(chunk_size, n)
                sample.append(self.simple_sample(amount) + i * chunk_size)
                n = n - amount
                i += 1
            sample = np.concatenate(sample)
        else:
            sample = self.simple_sample(n)
        if not(self.relative_indexing):
            sample = sample + position
        return sample

    def simple_sample(self, n):
        """get all samples from the next n items in a naive fashion

        Parameters
        ----------
        n : int
            the size of the chunk
        Returns
        -------
        sample : numpy.array
            the indices to be kept relative to the current position
            in the sample
        """
        k = hypergeometric_sample(self.N, self.K, n)  # get the sample size
        sample = sample_without_replacement(k, n, self.type)
        self.N = self.N - n
        self.K = self.K - k
        return sample


# function np.random.hypergeometric is buggy so I did my own implementation...
# (error, at least, line 784 in computation of variance: sample used instead
# of m, but this can't be all of it ?)
# following algo HRUA by Ernst Stadlober as implemented in numpy
# (https://github.com/numpy/numpy/blob/master/numpy/random/mtrand/
    #distributions.c and see original ref in zotero)
# this is 100 to 200 times slower than np.random.hypergeometric, but it works
# reliably
# could be optimized a lot if needed (for small samples in particular but also
# generally)
# seems at worse to require comparable execution time when compared to the
# actual rejection sampling, so probably not going to be so bad all in all
def hypergeometric_sample(N, K, n):
    """This function return the number of elements to sample from the next n
    items.
    """
    # handling edge cases
    if N == 0 or N == 1:
        k = K
    else:
        # using symmetries to speed up computations
        # if the probability of failure is smaller than the probability of
        # success, draw the failure count
        K_eff = min(K, N - K)
        # if the amount of items to sample from is larger than the amount of
        # items that will remain, draw from the items that will remain
        n_eff = min(n, N - n)
        N_float = np.float64(N)  # useful to avoid unexpected roundings

        average = n_eff * (K_eff / N_float)
        mode = np.floor((n_eff + 1) * ((K_eff + 1) / (N_float + 2)))
        variance = average * ((N - K_eff) / N_float) * \
            ((N - n_eff) / (N_float - 1))
        c1 = 2 * np.sqrt(2 / np.e)
        c2 = 3 - 2 * np.sqrt(3 / np.e)
        a = average + 0.5
        b = c1 * np.sqrt(variance + 0.5) + c2
        p_mode = (math.lgamma(mode + 1) + math.lgamma(K_eff - mode + 1) +
                  math.lgamma(n_eff - mode + 1) +
                  math.lgamma(N - K_eff - n_eff + mode + 1))
        # 16 for 16-decimal-digit precision in c1 and c2 (?)
        upper_bound = min(
            min(n_eff, K_eff) + 1, np.floor(a + 16 * np.sqrt(variance + 0.5)))

        while True:
            U = np.random.rand()
            V = np.random.rand()
            k = np.int64(np.floor(a + b * (V - 0.5) / U))
            if k < 0 or k >= upper_bound:
                continue
            else:
                p_k = math.lgamma(k + 1) + math.lgamma(K_eff - k + 1) + \
                    math.lgamma(n_eff - k + 1) + \
                    math.lgamma(N - K_eff - n_eff + k + 1)
                d = p_mode - p_k
                if U * (4 - U) - 3 <= d:
                    break
                if U * (U - d) >= 1:
                    continue
                if 2 * np.log(U) <= d:
                    break

        # retrieving original variables by symmetry
        if K_eff < K:
            k = n_eff - k
        if n_eff < n:
            k = K - k

    return k


# returns uniform samples in [0, N-1] without replacement
# the values 0.6 and 100 are based on empirical tests of the functions and
# would need to be changed if the functions are changed
def sample_without_replacement(n, N, dtype=np.int64):
    """Returns uniform samples in [0, N-1] without replacement. It will use
    Knuth sampling or rejection sampling depending on the parameters n and N.

    .. note:: the values 0.6 and 100 are based on empirical tests of the
    functions and would need to be changed if the functions are changed
    """
    if N > 100 and n / float(N) < 0.6:
        sample = rejection_sampling(n, N, dtype)
    else:
        sample = Knuth_sampling(n, N, dtype)
    return sample


# this one would benefit a lot from being cythonized, efficient if n close to N
# (np.random.choice with replace=False is cythonized and similar in spirit but
# not better because it shuffles
# the whole array of size N which is wasteful; once cythonized Knuth_sampling
# should be superior to it
# in all situation)
def Knuth_sampling(n, N, dtype=np.int64):
    """This is the usual sampling function when n is comparable to N
    """
    t = 0  # total input records dealt with
    m = 0  # number of items selected so far
    sample = np.zeros(shape=n, dtype=dtype)
    while m < n:
        u = np.random.rand()
        if (N - t) * u < n - m:
            sample[m] = t
            m = m + 1
        t = t + 1
    return sample


# maybe use array for the first iteration then use python native sets for
# faster set operations ?
def rejection_sampling(n, N, dtype=np.int64):
    """Using rejection sampling to keep a good performance if n << N
    """
    remaining = n
    sample = np.array([], dtype=dtype)
    while remaining > 0:
        new_sample = np.random.randint(0, N, remaining).astype(dtype)
        # keeping only unique element:
        sample = np.union1d(sample, np.unique(new_sample))
        remaining = n - sample.shape[0]
    return sample

"""
Profiling hypergeometric sampling + sampling without replacement together:

ChunkSize
10**2:
    hyper: 46s
    sample: 32s
10**3:
    hyper : 4.5s
    sample 6s
10**4:
    hyper 0.5s
    sample 4.5s
10**5:
    hyper 0.05s
    sample 4s
10**6:
    hyper 0.007s
    sample 5.7s
10**7:
    hyper 0.001s
    sample 10.33s
+ memory increase with chunk size

Should aim at having samples with around 100 000 elements.
This means sampling in 10**5 * sampled_proportion chunks.

profiling code:

import time
tt=[]
ra = range(8, 9)
for block_size in ra:
    t = time.clock()
    progress = 0
    b = 10**block_size
    for i in range(10**12//(10**3*b)):
        r = s.sample(10**3*b)
        progress = progress+100*(len(r)/10.**9)
        print(progress)
        if progress > 3:
            break
    tt.append(time.clock()-t)
for e, b in zip(tt, ra):
    print(b)
    print(e)

"""

### Profiling rejection sampling and Knuth sampling ###
# could create an automatic test for finding the turning point and offset
# between Knuth and rejection

# manual results:
# N	100
# n
# 1	R:60mu, K:30mu
# 10  R:83mu, K:54mu
# 100 R:7780mu, K:78mu
# N < 100 always Knuth
#
# N	1000
# n
# 1	R:60mu, K:248mu
# 10  R:65mu, K:450mu
# 100 R:150mu, K:523mu
# 1000 R:8610mu, K:785mu
# turning point: n/N between 0.5 and 0.75
#
# N 10**6
# 10**6 R:???, K:791ms
# 10**4 R:1ms, K:562ms
# 10**5 R:20ms, K:531ms
# turning point: n/N between 0.5 and 0.75
#
# N 10**9
# 10**6 R:174ms
# 10**7 R:2.7s
#
# N 10**18
# 1 R: 62mu
# 10 R: 62mu
# 10**3 R: 148mu
# 10**6 R: 131ms
