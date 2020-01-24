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

import h5py
import numpy as np
import argparse
import os.path as path
import os
import warnings

from ABXpy.misc.type_fitting import fit_integer_type


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
    """Numpy unique applied to the row only"""
    return (np.unique(np.ascontiguousarray(arr)
                      .view(np.dtype((np.void,
                                      arr.dtype.itemsize * arr.shape[1]))))
            .view(arr.dtype).reshape(-1, arr.shape[1]))


def collapse(scorefile, taskfile, fid):
    """Collapses the results for each triplets sharing the same on, across
    and by labels.

    """
    # We make the assumption that everything fits in memory...
    scorefid = h5py.File(scorefile)
    taskfid = h5py.File(taskfile)
    bys = taskfid['bys'][...]
    for by_idx, by in enumerate(bys):
        # print 'collapsing {0}/{1}'.format(by_idx + 1, len(bys))
        trip_attrs = taskfid['triplets']['by_index'][by_idx]

        tfrk = taskfid['regressors'][by]

        tmp = tfrk[u'indexed_data']
        indices = np.array(tmp)
        if indices.size == 0:
            continue
        tmp = scorefid['scores'][trip_attrs[0]:trip_attrs[1]]
        scores_arr = np.array(tmp)
        tmp = np.ascontiguousarray(indices).view(
            np.dtype((np.void, indices.dtype.itemsize * indices.shape[1])))
        n_indices = np.max(indices, 0) + 1
        assert np.prod(n_indices) < 18446744073709551615, "type not big enough"
        ind_type = fit_integer_type(np.prod(n_indices),
                                    is_signed=False)
        # encoding the indices of a triplet to a unique index
        new_index = indices[:, 0].astype(ind_type)
        for i in range(1, len(n_indices)):
            new_index = indices[:, i] + n_indices[i] * new_index

        permut = np.argsort(new_index)

        # collapsing the score
        sorted_scores = scores_arr[permut]
        sorted_index = new_index[permut]
        mean, unique_index, counts = unique(sorted_index, sorted_scores)

        # retrieving the triplet indices from the unique index.
        tmp = npdecode(unique_index, n_indices)

        regs = tfrk['indexed_datasets']
        indexes = []
        for reg in regs:
            indexes.append(tfrk['indexes'][reg][:])
        nregs = len(regs)

        for i, key in enumerate(tmp):
            aux = list()
            for j in range(nregs):
                aux.append(indexes[j][int(key[j])])
            score = mean[i]
            n = counts[i]
            result = aux + [by, score, int(n)]
            fid.write('\t'.join(map(str, result)) + u'\n')
            # results.append(aux + [context, score, n])
            # wf_tmp.write('\t'.join(map(str, results[-1])) + '\n')
    scorefid.close()
    taskfid.close()
    del taskfid
    # wf_tmp.close()
    # return results


def unique(index, scores):
    flag = np.concatenate(
        ([True], index[1:] != index[:-1], [True]))
    unique_idx = np.nonzero(flag)[0]
    counts = unique_idx[1:] - unique_idx[:-1]
    unique_index = index[unique_idx[:-1]]

    means = np.empty((len(counts)),)
    i = 0
    for a, c in enumerate(counts):
        means[a] = np.mean(scores[i:i+c])
        i += c
    means = (means + 1) / 2
    return means, unique_index, counts


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
        tfrk = aux[list(aux)[0]]
        regs = tfrk['indexed_datasets']
        string = u''
        for reg in regs:
            string += reg + '\t'
        string += 'by\tscore\tn\n'
        fid.write(string)
        taskfid.close()
        collapse(score_file, task_file, fid)


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Collapse results of ABX score on type of ABX triplet.',
        epilog='''Example usage:

$ ./analyze.py abx.score abx.task abx.csv

compute the average the scores in abx.score by type of ABX triplet
and output the results in tab separated csv format.''')
    parser.add_argument('scorefile', metavar='SCORE',
                        help='score file in hdf5 format')
    parser.add_argument('taskfile', metavar='TASK',
                        help='task file in hdf5 format')
    parser.add_argument('output', metavar='OUTPUT',
                        help='output file in csv format')
    return vars(parser.parse_args())


def main():
    args = parse_args()

    score_file = args['scorefile']
    if not path.exists(score_file):
        print('No such file: {}'.format(score_file))
        exit()

    task_file = args['taskfile']
    if not path.exists(task_file):
        print('No such file: {}'.format(task_file))
        exit()

    result_file = args['output']
    if os.path.exists(result_file):
        warnings.warn(
            'Overwriting results file ' + args['output'], UserWarning)
        os.remove(result_file)

    analyze(task_file, score_file, result_file)


if __name__ == '__main__':
    main()
