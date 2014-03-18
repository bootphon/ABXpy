# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 12:28:22 2013

@author: Thomas Schatz
"""

import h5py
import numpy as np    
import pandas


def analyze(task_file, score_file, result_file):
    #FIXME memory issues...
    bys = []
    by_scores = []
    with h5py.File(score_file) as s:
        for by in s['scores']:
            scores = s['scores'][by][...]
            score = np.mean((np.float64(np.reshape(scores, scores.shape[0]))+1)/2.)
            bys.append(by)
            by_scores.append(score)
    result = pandas.DataFrame({'by level': bys, 'average ABX score': by_scores})
    result.to_csv(result_file, sep = '\t')        
            
#FIXME write command-line interface