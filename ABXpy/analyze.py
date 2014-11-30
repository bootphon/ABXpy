from __future__ import division
"""This module is used to analyse the results of an ABX discrimination task

It collapses the result and give the mean score for each block of triplets
sharing the same on, across and by labels. It output a tab separated csv file
which columns are the relevant labels, the average score and the number of
triplets in the block. See `Files format <FilesFormat.html>`_ for a more
in-depth explanation.

It requires a score file and a task file.

Usage
-----
Form the command line:

.. code-block:: bash

    python analyze.py data.score data.abx data.csv

In python:

.. code-block:: python

    import ABXpy.analyze
    # Prerequisite: calculate a task data.abx, and a score data.score
    ABXpy.analyze.analyze(data.score, data.abx, data.csv)
"""
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 12:28:22 2013

@author: Thomas Schatz
"""
import h5py
import numpy as np
# import pandas
# import ast
import argparse
import os.path as path
import ABXpy.misc.type_fitting as type_fitting


# FIXME by_columns should be stored as attributes into the task file
# def analyze(task_file, score_file, analyze_file, by_columns=None):
#     """Analyse the results of a task

#     Parameters
#     ----------
#     task_file : string, hdf5 file
#         the file containing the triplets and pairs of the task
#     score_file : string, hdf5 file
#         the file containing the score of a task
#     analyse_file: string, csv file
#         the file that will contain the analysis
#     """
#     # FIXME memory issues ?
#     bys = []
#     by_scores = []
#     with h5py.File(score_file) as s:
#         for by in s['scores']:
#             scores = s['scores'][by][...]
#             scores = np.float64(np.reshape(scores, scores.shape[0]))
#             score = np.mean((scores + 1) / 2.)
#             bys.append(by)
#             by_scores.append(score)
#     df = pandas.DataFrame({'by level': bys, 'average ABX score': by_scores})
#     if not(by_columns is None):  # FIXME ugly fix
#         by_levels = np.array(map(ast.literal_eval, df['by level']))
#         d = dict(zip(by_columns, zip(*by_levels)))
#         for key in d:
#             df[key] = d[key]
#         del df['by level']
#     df.to_csv(analyze_file, sep='\t')


def npdecode(keys, max_ind):
    """Vectorized implementation of the decoding of the labels:
    i = (a1*n2 + a2)*n3 + a3 ...
    """
    res = np.empty((len(keys), len(max_ind)))
    aux = keys
    k = len(max_ind)
    for i in range(k - 1):
        res[:, k - 1 - i] = np.mod(aux, max_ind[k - 1 - i])
        aux = np.divide(aux - res[:, k - 1 - i], max_ind[k - 1 - i])
    res[:, 0] = aux
    return res


def unique_rows(arr):
    """Numpy unique applied to the row only.
    """
    return (np.unique(np.ascontiguousarray(arr)
                      .view(np.dtype((np.void,
                                      arr.dtype.itemsize * arr.shape[1]))))
            .view(arr.dtype).reshape(-1, arr.shape[1]))


def collapse(scorefile, taskfile, fid):
    """Collapses the results for each triplets sharing the same on, across and
    by labels.
    """
    # wf_tmp = open('tmp_pandas.txt', 'wb')
    scorefid = h5py.File(scorefile)
    taskfid = h5py.File(taskfile)
    nkeys = len(scorefid['scores'].keys())
    # results = []
    for key_idx, key in enumerate(scorefid['scores'].keys()):
        print 'collapsing {0}/{1}'.format(key_idx + 1, nkeys)
        context = key

        tfrk = taskfid['regressors'][key]

        tmp = tfrk[u'indexed_data']
        indices = np.array(tmp)
        if indices.size == 0:
            continue
        tmp = scorefid['scores'][key]
        scores_arr = np.array(tmp)
        tmp = np.ascontiguousarray(indices).view(
            np.dtype((np.void, indices.dtype.itemsize * indices.shape[1])))
        n_indices = np.max(indices, 0) + 1
        if np.prod(n_indices) > 18446744073709551615:
            print "type not big enough"
        ind_type = type_fitting.fit_integer_type(np.prod(n_indices),
                                                 is_signed=False)
        # encoding the indices of a triplet to a unique index
        new_index = indices[:, 0].astype(ind_type)
        for i in range(1, len(n_indices)):
            new_index = indices[:, i] + n_indices[i] * new_index

        permut = np.argsort(new_index)
        i_unique = 0
        # collapsing the score
        key_reg = new_index[permut[0]]
        mean = np.empty((len(permut), 3))
        mean[0] = [key_reg, scores_arr[permut[0]], 0]
        i_start = 0
        for i, p in enumerate(permut[1:]):
            i += 1
            if new_index[p] != key_reg:
                mean[i_unique, 1] = (np.mean(scores_arr[permut[i_start:i]])
                                     + 1) / 2
                mean[i_unique, 2] = i - i_start
                i_start = i
                i_unique += 1
                key_reg = new_index[p]
                mean[i_unique] = [key_reg, 0, 0]

        mean[i_unique] = [key_reg, (np.mean(scores_arr[permut[i_start:i + 1]])
                                    + 1) / 2, i - i_start + 1]
        mean = np.resize(mean, (i_unique + 1, 3))

        # retrieving the triplet indices from the unique index.
        tmp = npdecode(mean[:, 0], n_indices)

        regs = tfrk['indexed_datasets']
        indexes = []
        for reg in regs:
            indexes.append(tfrk['indexes'][reg][:])
        nregs = len(regs)

        for i, key in enumerate(tmp):
            aux = list()
            for j in range(nregs):
                aux.append(indexes[j][key[j]])
                # aux.append((indexes[regs[j]])[key[j]])
            score = mean[i, 1]
            n = mean[i, 2]
            result = aux + [context, score, int(n)]
            fid.write('\t'.join(map(str, result)) + '\n')
            # results.append(aux + [context, score, n])
            # wf_tmp.write('\t'.join(map(str, results[-1])) + '\n')

    # wf_tmp.close()
    # return results


def analyze(task_file, score_file, result_file):
    """Analyse the results of a task

    Parameters
    ----------
    task_file : string, hdf5 file
        the file containing the triplets and pairs of the task
    score_file : string, hdf5 file
        the file containing the score of a task
    result_file: string, csv file
        the file that will contain the analysis results
    """
    with open(result_file, 'w+') as fid:
        taskfid = h5py.File(task_file)
        aux = taskfid['regressors']
        tfrk = aux[aux.keys()[0]]
        regs = tfrk['indexed_datasets']
        string = ""
        for reg in regs:
            string += reg + "\t"
        string += "by\tscore\tn\n"
        fid.write(string)
        collapse(score_file, task_file, fid)
        # for r in results:
        #     fid.write('\t'.join(map(str, r)) + '\n')


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
    score_file = args['scorefile'][0]
    if not path.exists(score_file):
        print 'No such file:', score_file
        exit()
    task_file = args['taskfile'][0]
    if not path.exists(task_file):
        print 'No such file:', task_file
        exit()
    result_file = args['output'][0]
    # if not path.exists(outfile):
    # print 'No such file:', outfile
    # exit()

    analyze(task_file, score_file, result_file)
