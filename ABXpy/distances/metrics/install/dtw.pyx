# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 14:15:44 2014

@author: Thomas Schatz adapted from Gabriel Synaeve's code

The "feature" dimension is along the columns and the "time" dimension along the lines of arrays x and y.
    
The function do not verify its arguments, common problems are:
    shape of one array is n instead of (n,1)
    an array is not of the correct type DTYPE_t 
    the feature dimension of the two array do not match
    the feature and time dimension are exchanged
    the dist_array is not of the correct size or type
"""

import numpy as np
cimport numpy as np
cimport cython
from cpython cimport bool
ctypedef np.float64_t CTYPE_t # cost type
ctypedef np.intp_t IND_t # array index type
CTYPE = np.float64 # cost type 


def dtw(x, y, metric, normalized=False):
    if x.shape[0] == 0 or y.shape[0] == 0:
        raise ValueError('Cannot compute distance between empty representations')
    else:
        return _dtw(x.shape[0], y.shape[0], metric(x,y), normalized) 
    
 
# There was a bug at initialization in both Dan Ellis DTW and Gabriel's code:
#   Dan Ellis: do not take into account distance between the first frame of x and the first frame of y
#   Gabriel: init cost[0,:] and cost[:,0] by dist_array[0,:], resp. dist_array[:,0] instead of their cumsum 
#FIXME retest negligeability of min ?
cpdef _dtw(IND_t N, IND_t M, CTYPE_t[:,:] dist_array, bool normalized):
    cdef IND_t i, j
    cdef CTYPE_t[:,:] cost = np.empty((N, M), dtype=CTYPE)
    cdef CTYPE_t final_cost, cost_diag, cost_left, cost_up
    # initialization
    cost[0,0] = dist_array[0,0]
    for i in range(1,N):
        cost[i,0] = dist_array[i,0] + cost[i-1,0]
    for j in range(1,M):
        cost[0,j] = dist_array[0,j] + cost[0,j-1]
    # the dynamic programming loop
    for i in range(1,N):
        for j in range(1,M):
            cost[i,j] = dist_array[i,j] + min(cost[i-1,j], cost[i-1,j-1], cost[i,j-1])

    final_cost = cost[N-1, M-1]

    if normalized:
        path_len = 1
        i = N-1
        j = M-1
        while i > 0 and j > 0:
            c_up = cost[i-1, j]
            c_left = cost[i, j-1]
            c_diag = cost[i-1, j-1]
            if c_diag <= c_left and c_diag <= c_up:
                i -= 1
                j -= 1
            elif c_left <= c_up:
                j -= 1
            else:
                i -= 1
            path_len += 1
        if i == 0:
            path_len += j
        if j == 0:
            path_len += i
        final_cost /= path_len
    return final_cost
   
"""
import numpy as np
cimport numpy as np
cimport cython
ctypedef np.float64_t DTYPE_t # feature type (could be int)
ctypedef np.float64_t CTYPE_t # cost type
ctypedef np.intp_t IND_t # array index type
CTYPE = np.float64 # cost type 

cpdef DTW(DTYPE_t[:,:] x, DTYPE_t[:,:] y, CTYPE_t[:,:] dist_array):
    cdef IND_t N = x.shape[0]
    cdef IND_t M = y.shape[0]
    cdef IND_t K = x.shape[1]
    cdef IND_t i, j
    cdef CTYPE_t[:,:] cost = np.empty((N, M), dtype=CTYPE)
    # initialization
    cost[:,0] = dist_array[:,0]
    cost[0,:] = dist_array[0,:]
    # the dynamic programming loop
    for i in range(1, N):
        for j in range(1, M):
            cost[i,j] = dist_array[i,j] + min(cost[i-1,j], cost[i-1,j-1], cost[i,j-1])
    return cost[N-1,M-1] 
"""
