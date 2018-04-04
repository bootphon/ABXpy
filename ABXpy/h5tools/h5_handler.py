# -*- coding: utf-8 -*-
"""
Created on Tue Oct 15 09:48:31 2013

@author: Thomas Schatz
"""


"""Sort rows of a several two dimenional numeric dataset (possibly
with just one column) according to numeric key in two-dimensional key
dataset with just one column (the first dimension of all datasets
involved must match). The result replaces the original dataset buffer
size is in kilobytes.

Two things need improvement:

  * backup solution is too slow for big files

  * the case of very small files should be handled nicely by using
    internal sort

To gain time: could try to parallelize the sort, however not easy how
it would work for the merging part...  Also cythonizing the 'read
chunk' part might help getting more efficient when there are many
chunks

Also should write a function to determine buffer_size based on amount
of RAM and size of the file to be sorted: aim for 30 chunks or the
least possible without exploding the RAM, except if file can be loaded
in memory as a whole, then do internal sorting

"""

from __future__ import print_function
import numpy as np
import tempfile
import os
import h5py

from . import np2h5, h52np


class H5Handler(object):

    def __init__(self, h5file, keygroup, keyset, groups=None, datasets=None):
        if groups is None:
            groups = []
        if datasets is None:
            datasets = []
        paths = [g + '/' + d for g, d in zip(groups, datasets)]
        keypath = keygroup + '/' + keyset
        if keypath in paths:
            raise ValueError(
                'key dataset %s should not be in the list of datasets to be sorted: %s' % (keypath, paths))
        self.file = h5file
        self.groups = [keygroup] + groups
        self.datasets = [keyset] + datasets
        self.sources = zip(self.groups, self.datasets)

    # sort the content of several datasets with n lines and varying
    # number of columns in an h5file according to the order specified
    # in the first column of the 'key' dataset the result replaces the
    # original datasets order is specified by integers and sort is
    # done in increasing order buffer size is in Ko
    def sort(self, buffer_size=1000, o_buffer_size=1000, tmpdir=None):

        # first backup file to be sorted
        self.backupDir = tempfile.mkdtemp(dir=tmpdir)
        self.backup = os.path.join(self.backupDir, os.path.basename(self.file))
        # shutil.copyfile(self.file, self.backup)
        # FIXME if no backup is mad cannot recover from exceptions ...
        try:
            with H5TMP(tmpdir=tmpdir) as tmp:
                with h5py.File(self.file) as f:

                    # check file structure
                    for g, d in self.sources:
                        if not(g + '/' + d in f):
                            raise IOError(
                                'Dataset %s does not exist in group %s of file %s!' % (d, g, self.file))

                    # set tmp file structure (cannot be done in __init__
                    # because the tmp file is destroyed as soon as the 'with'
                    # statement is exited)
                    for g in np.unique(self.groups):
                        tmp.create_group(g)

                    # initialize variables
                    self.tmp = tmp
                    dsets = [f[g][d] for g, d in self.sources]
                    n_rows = [dset.shape[0] for dset in dsets]
                    if not(all([n_row == n_rows[0] for n_row in n_rows])):
                        raise IOError(
                            'First dimensions of all the datasets should be the same')
                    self.n_row = n_rows[0]
                    self.n_columns = [dset.shape[1] for dset in dsets]
                    self.dtypes = [dset.dtype for dset in dsets]
                    dset_weights = [
                        dset.shape[1] * dset.dtype.itemsize for dset in dsets]
                    self.dsets = dsets
                    self.line_weight = np.sum(dset_weights)
                    buf_rows = int(
                        round(buffer_size * 1000. / self.line_weight))
                    row = 0
                    n_chunks = 0

                    # here default to internal sort if not enough rows ?

                    # sort
                    while row <= self.n_row - buf_rows:
                        self.extract_chunk(row, row + buf_rows, n_chunks)
                        n_chunks = n_chunks + 1
                        row = row + buf_rows

                    if row < self.n_row:
                        self.extract_chunk(row, self.n_row, n_chunks)
                        n_chunks = n_chunks + 1

                # merge (tmp still open but f closed, both are important (tmp destruction and backup))
                # try block to allow backup recovery if something goes wrong
                try:
                    with np2h5.NP2H5(self.file) as o:
                        with h52np.H52NP(tmp) as i:

                            # buf_size =  ? for i: n_chunks * n_line_buf * totallinecost = buf_size ...
                            # for o ?

                            # create n_datasets*n_chunks input buffers
                            # number of rows
                            i_buf_rows = int(round(buf_rows / n_chunks))
                            # might need to set up an explicit case for dealing
                            # with files that can fit in one chunk and remove
                            # these asserts
                            assert i_buf_rows > 0
                            i_buf = []
                            for ix, (g, d) in enumerate(self.sources):
                                buf1 = []
                                for c in range(n_chunks):
                                    buf_size = self.dtypes[
                                        ix].itemsize * self.n_columns[ix] * i_buf_rows / 1000.
                                    buf1.append(
                                        i.add_dataset(g, d + '_' + str(c), buf_size))
                                i_buf.append(buf1)

                            # create n_datasets output buffers
                            o_buf_rows = int(
                                round(1000. * o_buffer_size / self.line_weight))
                            assert o_buf_rows > 0
                            o_buf = []
                            for ix, (g, d) in enumerate(self.sources):
                                buf_size = self.dtypes[
                                    ix].itemsize * self.n_columns[ix] * o_buf_rows / 1000.
                                o_buf.append(o.add_dataset(g, d, self.n_row, self.n_columns[
                                             ix], buf_size, buf_size, self.dtypes[ix], overwrite=True))

                            # some redundancy could be removed from the following while + flushing
                            # while not all input datasets empty:
                            # sufficient to check key buffers only
                            while not(all([buf.dataset_empty() for buf in i_buf[0]])):

                                # find min of maxes (current tails) in key
                                min_tail = min(
                                    [buf.current_tail() for buf in i_buf[0] if not(buf.isempty())])

                                # find for each chunk the amount to be read
                                amounts = [
                                    buf.nb_lower_than(min_tail) for buf in i_buf[0]]

                                # get the order on key for the concatenated
                                # data
                                data = []
                                # for all chunks: read up to the appropriate
                                # index, concatenate, sort and output
                                for c in range(n_chunks):
                                    if amounts[c] > 0:
                                        data.append(
                                            i_buf[0][c].read(amounts[c]))
                                data = np.concatenate(data)
                                order = np.argsort(data[:, 0])
                                o_buf[0].write(data[order, :])

                                # for all other dset use the order from the
                                # key:
                                for d in range(1, len(self.datasets)):
                                    data = []
                                    # for all chunks: read up to the
                                    # appropriate index, concatenate, sort and
                                    # output
                                    for c in range(n_chunks):
                                        if amounts[c] > 0:
                                            data.append(
                                                i_buf[d][c].read(amounts[c]))
                                    data = np.concatenate(data)
                                    o_buf[d].write(data[order, :])

                            # flush the buffers to finish
                            data = []
                            for c in range(n_chunks):
                                if not(i_buf[0][c].buffer_empty()):
                                    # read without argument gives the whole
                                    # buffer
                                    data.append(i_buf[0][c].read())
                            if data:  # False iff list is empty
                                data = np.concatenate(data)
                                order = np.argsort(data[:, 0])
                                o_buf[0].write(data[order, :])

                            for d in range(1, len(self.datasets)):
                                data = []
                                for c in range(n_chunks):
                                    if not(i_buf[d][c].buffer_empty()):
                                        # read without argument gives the whole
                                        # buffer
                                        data.append(i_buf[d][c].read())
                                if data:  # False iff list is empty
                                    data = np.concatenate(data)
                                    o_buf[d].write(data[order, :])

                # use the backup
                except:
                    # shutil.copyfile(self.backup, self.file) #FIXME not usable
                    # if backup isn't made
                    raise
        # delete the backup
        finally:
            # os.remove(self.backup)
            os.rmdir(self.backupDir)

    def extract_chunk(self, i_start, i_end, chunk_id):

        # get key order for the chunk
        key = self.dsets[0][i_start:i_end, 0]
        order = np.argsort(key)

        # sort all datasets according to it and store them
        for i, d in enumerate(self.dsets):
            # sort chunk
            chunk = d[i_start:i_end, :]
            chunk = chunk[order, :]
            # store chunk
            chunk_name = self.datasets[i] + '_' + str(chunk_id)
            g = self.groups[i]
            self.tmp[g].create_dataset(
                chunk_name, (i_end - i_start, self.n_columns[i]), dtype=d.dtype)
            self.tmp[g][chunk_name][:, :] = chunk


# Class for creating a temporary h5 file. Should be used with the 'with'
# statement. The temporary file will be erased upon exiting the 'with'
# statement
class H5TMP(object):

    def __init__(self, tmpdir=None):
        self.tmpdir = tempfile.mkdtemp(dir=tmpdir)
        self.tmpfile = os.path.join(self.tmpdir, 'tmp.h5')

    def __enter__(self):
        self.tmp = h5py.File(self.tmpfile)
        return self.tmp

    def __exit__(self, eType, eValue, eTrace):
        try:
            self.tmp.close()
            os.remove(self.tmpfile)
            os.rmdir(self.tmpdir)
        except:
            print('problem')
            # here could log a warning...
            pass


def test():

    # generate random h5 file
    n1 = 10
    n2 = 1000
    np.random.seed(42)
    folder = tempfile.mkdtemp()
    with h5py.File(os.path.join(folder, 'tmp.h5')) as fh:
        fh.create_group('key')
        fh['key'].create_dataset('k', (n2 * n1, 1), np.int64)
        fh.create_group('data')
        fh['data'].create_dataset('f', (n2 * n1, 3), np.float64)
        fh['data'].create_dataset('i', (n2 * n1, 5), np.int64)
        for i in range(n1):
            keys = np.random.randint(10 ** 12, size=(n2, 1))
            fh['key']['k'][i * n2:(i + 1) * n2, :] = keys
            floats = np.random.rand(n2, 3)
            fh['data']['f'][i * n2:(i + 1) * n2, :] = floats
            integers = np.random.randint(10 ** 12, size=(n2, 5))
            fh['data']['i'][i * n2:(i + 1) * n2, :] = integers

    #folder = '/var/folders/ma/maqYoEehEsiaVpQWYhnOr++++TY/-Tmp-/tmpaLxTaQ'
    # test sort on it
    h = H5Handler(
        os.path.join(folder, 'tmp.h5'), 'key', 'k', ['data', 'data'], ['f', 'i'])
    h.sort(100, 100)

    # get the same in a regular arrays and compare with regular sorting
    # ...
