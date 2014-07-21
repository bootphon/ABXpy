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
# import ABXpy.h5tools.np2h5 as np2h5
# import ABXpy.h5tools.h5_handler as h5_handler
import ABXpy.misc.type_fitting as type_fitting


def npdecode(keys, max_ind):
    res = np.empty((len(keys), len(max_ind)))
    aux = keys
    k = len(max_ind)
    for i in range(k - 1):
        res[:, k - 1 - i] = np.mod(aux, max_ind[k - 1 - i])
        aux = np.divide(aux - res[:, k - 1 - i], max_ind[k - 1 - i])
    res[:, 0] = aux
    return res


def decode(keys, max_ind):
    res = np.empty((len(max_ind)), dtype=np.int8)
    aux = keys / np.prod(max_ind)
    for i, n in enumerate(max_ind):
        aux = aux * n
        res[i] = int(aux)
        aux = aux - res[i]
    return res


def unique_rows(arr):
    return (np.unique(np.ascontiguousarray(arr)
                      .view(np.dtype((np.void,
                                      arr.dtype.itemsize * arr.shape[1]))))
            .view(arr.dtype).reshape(-1, arr.shape[1]))


def collapse(scorefile, taskfile):
    wf_tmp = open('tmp_pandas.txt', 'wb')
    scorefid = h5py.File(scorefile)
    taskfid = h5py.File(taskfile)
    nkeys = len(scorefid['scores'].keys())
    results = []
    for key_idx, key in enumerate(scorefid['scores'].keys()):
        # if key_idx % 500 == 0:
        print 'collapsing {0}/{1}'.format(key_idx + 1, nkeys)
        # if(key_idx>16): break
        # print key
        context = key

        tfrk = taskfid['regressors'][key]

        tmp = tfrk[u'indexed_data']
        indices = np.array(tmp)
        if indices.size == 0:
            continue
        tmp = scorefid['scores'][key]
        scores_arr = np.array(tmp)
        #unique = unique_rows(indices)
        tmp = np.ascontiguousarray(indices).view(
            np.dtype((np.void, indices.dtype.itemsize * indices.shape[1])))
        # del tfrk['encoded_indexed_dataset']
        # n_indices = np.max(indices, 0) + 100
        n_indices = np.max(indices, 0) + 1
        if np.prod(n_indices) > 18446744073709551615:
            print "type not big enough"
        ind_type = type_fitting.fit_integer_type(np.prod(n_indices),
                                                 is_signed=False)
        new_index = indices[:, 0].astype(ind_type)
        for i in range(1, len(n_indices)):
            new_index = indices[:, i] + n_indices[i] * new_index
        # aux = np.arange(len(new_index))
        # aux = np.hstack((new_index[:, None], aux[:, None]))

        permut = np.argsort(new_index)
        i_unique = 0
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
            results.append(aux + [context, score, n])
            wf_tmp.write('\t'.join(map(str, results[-1])) + '\n')

        # dset = tfrk.create_dataset("encoded_indexed_dataset", data=aux)
        # tfrk['encoded_indexed_dataset'] = aux
        # handler = h5_handler.H5Handler(taskfile, '/regressors/',
        #                                str(key) + '/encoded_indexed_dataset')
        # handler.sort()

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
    # if not path.exists(outfile):
    # print 'No such file:', outfile
    # exit()

    write(collapse(scorefile, taskfile), taskfile, outfile)
