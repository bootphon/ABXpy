# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 16:30:23 2013

@author: Thomas Schatz
"""


"""Class for reading efficiently h5 files, with functions useful for merging sorted datasets.
"""
# FIXME: Some code is shared by H52NP and NP2H5: could have a superclass:
# optionally_h5_context_manager who would consist in implementing
# __init__, __enter__, __exit__ where a filename or a file handle can be
# passed and the file should be handled by the context manager only if a
# filename is passed.

# FIXME: Also the functionalities specific to sorted datasets could be put in a subclass.

import numpy as np
import bisect
import h5py


class H52NP(object):

    # sink is the name of the HDF5 file to which to write, buffer size is in
    # kilobytes

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

    def __enter__(self):
        if not(self.file_open):
            self.file = h5py.File(self.filename)
            self.file_open = True
        return self

    def __exit__(self, eType, eValue, eTrace):
        if self.file_open and self.manage_file:
            try:
                self.file.close()
                self.file_open = False
            except:
                if eValue is not None:
                    # the first exception will be raised, but could log a
                    # warning here ...
                    pass
                else:
                    raise

    def add_dataset(self, group, dataset, buf_size=100, minimum_occupied_portion=0.25):
        if self.file_open:
            buf = H52NPbuffer(
                self, group, dataset, buf_size, minimum_occupied_portion)
            self.buffers.append(buf)
            return buf
        else:
            raise IOError(
                "Method add_dataset of class H52NP can only be used within a 'with' statement!")


class H52NPbuffer(object):

    def __init__(self, parent, group, dataset, buf_size, minimum_occupied_portion):

        assert parent.file_open

        # get info from dataset
        # fail if dataset do not exist
        if not(group + '/' + dataset in parent.file):
            raise IOError('Dataset %s already exists in file %s!' %
                          (dataset, parent.filename))
        dset = parent.file[group][dataset]
        self.n_rows = dset.shape[0]
        self.n_columns = dset.shape[1]
        self.type = dset.dtype
        self.dataset = dset
        self.dataset_ix = 0
        # could add checks: no more than 2 dims, etc.

        self.parent = parent
        self.minimum_occupied_portion = minimum_occupied_portion

        # initialize buffer
        row_size = self.n_columns * self.type.itemsize / \
            1000.  # entry size in kilobytes
        self.buf_len = int(round(buf_size / row_size))
        # buf_ix represents the number of free rows in the buffer. Here the
        # buffer is empty
        self.buf_ix = self.buf_len
        self.buf = np.zeros((self.buf_len, self.n_columns), self.type)
        # fill it
        self.refill_buffer()

    # read and consume, refill automatically if the buffer becomes empty, if
    # there is not enough data left, just send less than what was asked
    def read(self, amount=None):

        assert self.parent.file_open

        if not(amount is None) and amount <= 0:
            raise ValueError(
                'The amount to be read in h52np.read must be strictly positive')

        if amount is None:
            amount = self.buf_len - self.buf_ix

        if self.isempty():
            raise StopIteration

        amount_found = 0
        data = []
        while amount_found < amount and not(self.isempty()):
            needed = amount - amount_found
            amount_in_buffer = self.buf_len - self.buf_ix
            if amount_in_buffer > needed:  # enough data in buffer
                next_buf_ix = self.buf_ix + needed
                amount_found = amount
            else:
                # not enough data in buffer (or just enough)
                next_buf_ix = self.buf_len
                amount_found = amount_found + amount_in_buffer

            # the np.copy is absolutely necessary here to avoid ugly side effects...
            data.append(np.copy(self.buf[self.buf_ix:next_buf_ix, :]))
            self.buf_ix = next_buf_ix
            # fill buffer or not, according to refill policy and current buffer
            # state
            self.refill_buffer()
        return np.concatenate(data)

    def refill_buffer(self):
        if not(self.dataset_ix == self.n_rows):
            # for now one policy is implemented: if less than
            # self.minimum_occupied_portion of the full capacity is occupied
            # the buffer is refilled
            occupied_portion = 1. - float(self.buf_ix) / float(self.buf_len)
            if occupied_portion < self.minimum_occupied_portion:
                # set useful variables
                curr_ix = self.dataset_ix
                next_ix = curr_ix + self.buf_ix
                next_buf_ix = next_ix - self.n_rows
                amount_in_buffer = self.buf_len - self.buf_ix
                # take care of not going out of the dataset
                next_buf_ix = max(next_buf_ix, 0)
                next_ix = min(next_ix, self.n_rows)
                # move old data
                self.buf[next_buf_ix:next_buf_ix+amount_in_buffer, :] = self.buf[self.buf_ix:,:]
                # add new data
                self.buf[next_buf_ix+amount_in_buffer:, :] = self.dataset[curr_ix:next_ix,:]
                # update indices
                self.buf_ix = next_buf_ix
                self.dataset_ix = next_ix

    # true only if the input file has been totally read and the buffer is empty
    def isempty(self):
        assert self.parent.file_open
        return self.dataset_ix == self.n_rows and self.buf_ix == self.buf_len

    def buffer_empty(self):
        assert self.parent.file_open
        return self.buf_ix == self.buf_len

    def dataset_empty(self):
        assert self.parent.file_open
        return self.dataset_ix == self.n_rows

    # return the last row currently in the buffer (useful for merge sort...)
    # assuming the data is one-column
    def current_tail(self):
        assert self.parent.file_open
        assert self.n_columns == 1
        return self.buf[-1, 0]

    # returns the number of element in the buffer lower or equal to x,
    # assuming the data is one-column ordered and sorted
    def nb_lower_than(self, x):
        assert self.parent.file_open
        assert self.n_columns == 1
        return bisect.bisect_right(self.buf[self.buf_ix:, :], x)
