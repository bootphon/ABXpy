# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 12:28:22 2013

@author: Thomas Schatz
"""

import h5py
import numpy as np
import pandas
import ast


def analyze(task_file, score_file, analyze_file):
    #FIXME memory issues ?
    bys = []
    by_scores = []
    with h5py.File(score_file) as s:
        for by in s['scores']:
            scores = s['scores'][by][...]
            scores = np.float64(np.reshape(scores, scores.shape[0]))
            score = np.mean((scores+1)/2.)
            bys.append(by)
            by_scores.append(score)
    df = pandas.DataFrame({'by level': bys, 'average ABX score': by_scores})
    by_levels = np.array(map(ast.literal_eval, df['by level']))
    d = dict(zip(by, zip(*by_levels)))
    for key in d:
        df[key] = d[key]
    del df['by level']
    df.to_csv(analyze_file, sep='\t')

#FIXME write command-line interface
