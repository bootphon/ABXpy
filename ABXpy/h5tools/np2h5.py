# -*- coding: utf-8 -*-
"""Created on Thu Sep 19 13:46:18 2013

@author: Thomas Schatz

Class for efficiently writing to disk (in a specified dataset of a
HDF5 file) simple two-dimensional numpy arrays that are incrementally
generated along the first dimension.  It uses buffers to avoid small
I/O.

It needs to be used within a 'with' statement, so as to handle buffer
flushing and opening and closing of the underlying HDF5 file smoothly.

Buffer size should be chosen according to speed/memory trade-off. Due
to cache issues there is probably an optimal size.

The size of the dataset to be written must be known in advance,
excepted when overwriting an existing dataset. Not writing exactly
the expected amount of data causes an Exception to be thrown excepted
is the fixed_size option was set to False when adding the dataset.

"""

import numpy as np
import h5py

class NP2H5(object):
    # sink is the name of the HDF5 file to which to write, buffer size
    # is in kilobytes
    def __init__(self, h5file):
        # set up output file and buffer list
        if isinstance(h5file, str):
            self.manage_file = True
            self.filename = h5file
            self.file_open = False
        else:  # supposed to be a h5 file handle
            self.manage_file = False
            self.file_open = True
            self.file = h5file
            self.filename = h5file.filename
        self.buffers = []

    # open HDF5 file in 'with' statement
    def __enter__(self):
        if not(self.file_open):
            self.file = h5py.File(self.filename)
            self.file_open = True
        return self

    # flush buffers and close HDF5 file in 'with' statement
    def __exit__(self, eType, eValue, eTrace):
        try:
            if self.file_open:
                for buf in self.buffers:
                    buf.flush()
                if self.manage_file:
                    self.file.close()
                    self.file_open = False
            # if there was an error, delete dataset, otherwise check that the
            # amount of data actually written is consistent with the size of
            # the datasets
            if eValue is not None:
                if not(self.file_open):
                    self.file = h5py.File(self.filename)
                    self.file_open = True
                for buf in self.buffers:
                    buf.delete()
                if self.manage_file:
                    self.file.close()
                    self.file_open = False
            # check that all buffers were completed (defaults to true for
            # dataset without a fixed size)
            elif not(all([buf.iscomplete() for buf in self.buffers])):
                raise Warning('File {}, the amount of data actually written '
                              'is not consistent with the size of the datasets'
                              .format(self.filename))
        except:
            # raise the first exception
            if eValue is not None:
                # FIXME: the first exception will be raised, but could log a
                # warning here ...
                pass
            else:
                raise

    def add_dataset(self, group, dataset, n_rows=0, n_columns=None,
                    chunk_size=100, buf_size=100, item_type=np.int64,
                    overwrite=False, fixed_size=True):
        if n_columns is None:
            raise ValueError(
                'You have to specify the number of columns of the dataset.')
        if self.file_open:
            buf = NP2H5buffer(self, group, dataset, n_rows, n_columns,
                              chunk_size, buf_size, item_type,
                              overwrite, fixed_size)
            self.buffers.append(buf)
            return buf
        else:
            raise IOError("Method add_dataset of class NP2H5 can only "
                          "be used within a 'with' statement!")


class NP2H5buffer(object):
    # buf_size in Ko
    def __init__(self, parent, group, dataset, n_rows, n_columns,
                 chunk_size, buf_size, item_type, overwrite, fixed_size):

        assert parent.file_open

        # check coherency of arguments if size is fixed or not
        if n_rows == 0 and fixed_size:
            raise ValueError(
                'A dataset with a fixed size cannot have zero lines')
        if overwrite and not(fixed_size):
            raise ValueError(
                'Cannot overwrite a dataset without a specified fixed size')
        self.fixed_size = fixed_size

        # check type argument
        # dtype call is needed to access the itemsize attribute in case a
        # built-in type was specified
        self.type = np.dtype(item_type)
        if self.type.itemsize == 0:
            raise AttributeError('NP2H5 can only be used with numpy arrays '
                                 'whose items have a fixed size in memory')

        # initialize buffer
        self.buf_len = nb_lines(self.type.itemsize, n_columns, buf_size)
        self.buf = np.zeros([self.buf_len, n_columns], dtype=self.type)
        self.buf_ix = 0

        # set up output dataset
        self.dataset_ix = 0
        # fail if dataset already exists and overwrite=False otherwise create
        # it or overwrite it
        if group + '/' + dataset in parent.file:
            if overwrite:
                self.dataset = parent.file[group][dataset]
                if (self.dataset.shape[0] != n_rows or
                    self.dataset.shape[1] != n_columns or
                    self.dataset.dtype != self.type):
                    raise IOError('Overwriting a dataset is only possible if '
                                  'it already has the correct shape and dtype')
            else:
                raise IOError('Dataset {} already exists in file {}!'
                              .format(dataset, parent.filename))
        else:
            # if necessary create group
            try:
                g = parent.file[group]
            except KeyError:
                g = parent.file.create_group(group)
            # create dataset
            if self.fixed_size:
                # would it be useful to chunk here?
                g.create_dataset(dataset, (n_rows, n_columns), dtype=self.type)
            else:
                chunk_lines = nb_lines(
                    self.type.itemsize, n_columns, chunk_size)
                g.create_dataset(dataset, (n_rows, n_columns),
                                 dtype=self.type,
                                 chunks=( chunk_lines, n_columns),
                                 maxshape=(None, n_columns))
            self.dataset = parent.file[group][dataset]

        # store useful parameters
        self.n_rows = n_rows
        self.n_columns = n_columns
        self.parent = parent

    def write(self, data):
        # fail if not used in a with statement of a parent NP2H5 object
        if not(self.parent.file_open):
            raise IOError("Method write of class NP2H5buffer can only be used "
                          "within a 'with' statement of parent NP2H5 object!")

        target_ix = self.buf_ix + data.shape[0]
        # if size is not of fixed size, check that it is big enough
        if not(self.fixed_size):
            necessary_rows = self.dataset_ix + \
                self.buf_len * (target_ix // self.buf_len)
            if necessary_rows > self.n_rows:
                self.n_rows = necessary_rows
                # maybe should use larger increments ? could use chunk size as
                # a basis for the increments instead of buf_len if useful
                self.dataset.resize((self.n_rows, self.n_columns))
        # while buffer is full dump it to file
        while target_ix >= self.buf_len:
            # fill buffer
            buffer_space = self.buf_len - self.buf_ix
            self.buf[self.buf_ix:] = data[:buffer_space, :]
            # dump buffer to file
            ix_start = self.dataset_ix
            ix_end = self.dataset_ix + self.buf_len
            self.dataset[ix_start:ix_end, :] = self.buf
            self.dataset_ix = ix_end
            # reset variables for next iteration
            self.buf_ix = 0
            data = data[buffer_space:, :]
            target_ix = target_ix - self.buf_len
        # put remaining data in buffer
        self.buf[self.buf_ix:target_ix, :] = data
        self.buf_ix = target_ix

    def flush(self):
        assert self.parent.file_open
        if self.buf_ix > 0:
            ix_start = self.dataset_ix
            ix_end = self.dataset_ix + self.buf_ix
            if not(self.fixed_size) and ix_end > self.n_rows:
                self.dataset.resize((ix_end, self.n_columns))
            self.dataset[ix_start:ix_end, :] = self.buf[:self.buf_ix]
            self.dataset_ix = ix_end
            self.buf_ix = 0

    def delete(self):
        assert self.parent.file_open
        del self.dataset

    def iscomplete(self):
        if self.fixed_size:
            test = self.dataset_ix == self.n_rows
        else:
            test = True
        return test


# item_size given in bytes, size_in_mem given in kilobytes
def nb_lines(item_size, n_columns, size_in_mem):
    return int(round(size_in_mem * 1000. / (item_size * n_columns)))
