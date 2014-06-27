#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------
# file: collapse_results.py
# date: Tue May 06 17:03 2014
# author:
# Maarten Versteegh
# github.com/mwv
# maartenversteegh AT gmail DOT com
#
# Licensed under GPLv3
# ------------------------------------
"""collapse_results:

"""

from __future__ import division

import h5py
import numpy as np
import argparse
import os.path as path
# phone, context, talker
# phoneA, phoneB, context, talkerA, talkerX

def unique_rows(arr):
    return (np.unique(np.ascontiguousarray(arr)
                      .view(np.dtype((np.void,
                                      arr.dtype.itemsize * arr.shape[1]))))
            .view(arr.dtype).reshape(-1, arr.shape[1]))
import pandas as pd

def collapse(scorefile, taskfile):
    wf_tmp = open('tmp_pandas.txt', 'w')
    scorefid = h5py.File(scorefile)
    taskfid = h5py.File(taskfile)
    nkeys = len(scorefid['scores'].keys())
    results = []
    for key_idx, key in enumerate(scorefid['scores'].keys()):
        #if key_idx % 500 == 0:
        print 'collapsing {0}/{1}'.format(key_idx+1, nkeys)
        #if(key_idx>16): break
        #print key
        context = key

        tfrk = taskfid['regressors'][key]
        tmp = tfrk[u'indexed_data']
        indices = np.array(tmp)
        tmp = scorefid['scores'][key]
        scores_arr = np.array(tmp)
        #unique = unique_rows(indices)

        regs = tfrk['indexed_datasets']
        nregs = len(regs)

        indexes = tfrk['indexes']

        df=pd.DataFrame(np.hstack((indices,scores_arr)))
        groups=df.groupby(range(nregs))
        themean=(groups.mean()+1.0)/2
        themean=themean[nregs]
        thecount=(groups.count())
        thecount=thecount[nregs]
        for k_id,key in enumerate(themean.keys()):
            aux = np.array(indexes[regs[0]])[list(key)]
            score=themean[key]
            n=thecount[key]
            results.append(tuple(aux) + (context, score, n))
            wf_tmp.write('\t'.join(map(str, results[-1])) + '\n')

    wf_tmp.close()
    return results


def write(results, taskfile, outfile):
    with open(outfile, 'w') as fid:
        taskfid = h5py.File(taskfile)
        aux = taskfid['regressors']
        tfrk = aux[aux.keys()[0]]
        regs = tfrk['indexed_datasets']
        string = ""
        for reg in regs:
            string += reg + "\t"
        string += "by\tscore\tn\n"
        fid.write(string)
        for r in results:
            fid.write('\t'.join(map(str, r)) + '\n')


def parse_args():
    parser = argparse.ArgumentParser(
        prog='collapse_results.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Collapse results of ABX on by conditions.',
        epilog="""Example usage:

$ ./collapse_results.py abx.score abx.task abx_collapsed.txt

collapses the scores in abx.score by the conditions in abx.task and outputs
to plain text format in abx_collapsed.txt.""")
    parser.add_argument('scorefile', metavar='SCORE',
                        nargs=1,
                        help='score file in hdf5 format')
    parser.add_argument('taskfile', metavar='TASK',
                        nargs=1,
                        help='task file in hdf5 format')
    parser.add_argument('output', metavar='OUTPUT',
                        nargs=1,
                        help='plain text output file')
    return vars(parser.parse_args())


if __name__ == '__main__':
    args = parse_args()
    scorefile = args['scorefile'][0]
    if not path.exists(scorefile):
        print 'No such file:', scorefile
        exit()
    taskfile = args['taskfile'][0]
    if not path.exists(taskfile):
        print 'No such file:', taskfile
        exit()
    outfile = args['output'][0]
        #if not path.exists(outfile):
        #print 'No such file:', outfile
        #exit()

    write(collapse(scorefile, taskfile), taskfile, outfile)
