# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 01:47:42 2014

@author: Thomas Schatz
"""
import numpy as np
import scipy

# compute cosine distances between all possible pairs of lines in the x and y matrix
# x and y should be 2D numpy arrays with "features" on the lines and "times" on the columns
# x, y must be float arrays    
def cosine_distance(x,y):
    assert x.dtype == np.float64 and y.dtype == np.float64
    x2 = np.sqrt(np.sum(x**2, axis=1))
    y2 = np.sqrt(np.sum(y**2, axis=1))
    ix = x2 == 0.
    iy = y2 == 0.
    d = np.dot(x, y.T)/(np.outer(x2,y2))
    d = np.float64(scipy.arccos(d)/np.pi) # costly in time (half of the time), so check if really useful for dtw   
    d[ix,:] = 1.
    d[:, iy] = 1.
    d[ix, iy] = 0.
    assert np.all(d>=0)
    return d  