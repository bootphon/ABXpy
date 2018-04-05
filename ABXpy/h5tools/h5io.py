# -*- coding: utf-8 -*-
"""
Created on Sun Jan 19 17:06:15 2014

@author: Thomas Schatz
"""

# make sure the rest of the ABXpy package is accessible
import os
import sys
from six import iteritems
import collections
import os
from past.builtins import basestring

import h5py
import numpy as np


package_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
if not(package_path in sys.path):
    sys.path.append(package_path)
import ABXpy.misc.type_fitting as type_fitting
# FIXME should remove above dependency on rest of ABX...

from . import np2h5


# API functions:
#   __init__, write, sort, find, read

class H5IO(object):

    # example call without shared indexes and without fused datasets: H5IO('file.h5', ['talker', 'language', 'age'], {'talker': ['t1', 't2', 't3'], 'language': ['French', 'English']})
    # example call with shared indexes and with fused datasets:
    # H5IO('file.h5', {'talker1': 'talker', 'talker2': 'talker', 'language':
    # 'language', 'age1': None, 'age2': None}, {'talker': ['t1', 't2', 't3'],
    # 'language': ['French', 'English']}, {'talkers': ['talker1', 'talker2']})

    def __init__(self, filename, datasets=None, indexes=None, fused=None, group='/'):

        # format and check inputs
        if indexes is None:
            indexes = {}
        if fused is None:
            fused = {}
        if datasets is not None:
            if isinstance(datasets, collections.Mapping):
                indexed_datasets = [
                    key for key, value in iteritems(datasets) if not(value is None)]
                indexed_datasets_indexes = [
                    value for value in datasets.values() if not(value is None)]
                if not(set(datasets.values()).difference([None]) == set(indexes.keys())):
                    raise ValueError(
                        'Indexes and datasets declaration are inconsistent.')
                datasets = list(datasets)
            else:
                indexed_datasets = list(indexes)
                indexed_datasets_indexes = list(indexes)
                if not(set(indexes.keys()).issubset(datasets)):
                    raise ValueError(
                        'Indexes and datasets declaration are inconsistent.')
            # check that all datasets to be fused are indexed
            all_fused_dsets = [dset for dsets in fused.values()
                               for dset in dsets]
            for dset in all_fused_dsets:
                if not(dset in indexed_datasets):
                    raise ValueError(
                        'Only datasets for which an index was provided can be fused.')

        # create HDF5 file if it doesn't exist
        try:  # first check if file exists
            with open(filename):
                if not(datasets is None):
                    raise IOError('File %s already exists' % filename)
            with h5py.File(filename) as f:
                try:
                    f[group]
                except KeyError:
                    raise IOError(
                        "File %s doesn't contain a group named %s" % (filename, group))
        except IOError:  # if file doesn't exist create it
            if datasets is None:
                raise IOError("File %s doesn't exist" % filename)
            with h5py.File(filename) as f:
                if not(group in f):  # handler error here ...
                    g = f.create_group(group)
                else:
                    g = f[group]
                # general structure
                g.attrs['empty'] = True
                g.attrs['sorted'] = False
                # h5 dtype for storing variable length strings
                str_dtype = h5py.special_dtype(vlen=str)
                g.create_dataset(
                    'managed_datasets', data=datasets, dtype=str_dtype)
                raw_datasets = list(set(datasets).difference(indexed_datasets))
                if raw_datasets:
                    g.create_dataset(
                        'raw_datasets', data=raw_datasets, dtype=str_dtype)
                # indexed datasets
                if indexed_datasets:
                    g.create_dataset(
                        'indexed_datasets', data=indexed_datasets, dtype=str_dtype)
                    g.create_dataset(
                        'indexed_datasets_indexes', data=indexed_datasets_indexes, dtype=str_dtype)
                    index_group = g.create_group('indexes')
                    for key, value in iteritems(indexes):
                        index_group.create_dataset(
                            key, data=value, dtype=get_dtype(value))
                    non_fused = [
                        dset for dset in indexed_datasets if not(dset in all_fused_dsets)]
                    if non_fused:
                        g.create_dataset(
                            'non_fused_datasets', data=non_fused, dtype=str_dtype)
                # fused datasets
                if fused:
                    g.create_dataset(
                        'fused_datasets', data=list(fused), dtype=str_dtype)
                    h = g.create_group('fused')
                    for name, fused_dsets in iteritems(fused):
                        i = h.create_group(name)
                        i.create_dataset(
                            'datasets', data=fused_dsets, dtype=str_dtype)
                        nb_levels = [len(indexes[indexed_datasets_indexes[
                                         indexed_datasets.index(dset)]]) for dset in fused_dsets]
                        i.create_dataset(
                            'nb_levels', data=nb_levels, dtype=np.uint64)

        # instantiate h5io runtime object from (possibly newly created) file
        self.filename = filename
        self.group = group
        self.__load__()

    def __load__(self):
        self.__load_metadata__()
        # FIXME: self.load_data() # this implementation supposes that the
        # datasets can be held in memory without problems

    def __load_metadata__(self):
        with h5py.File(self.filename) as f:
            g = f[self.group]
            self.is_empty = g.attrs['empty']
            self.is_sorted = g.attrs['sorted']
            self.managed_datasets = list(g['managed_datasets'][...])
            if 'raw_datasets' in g:
                self.raw_datasets = list(g['raw_datasets'][...])
            else:
                self.raw_datasets = []
            if 'indexed_datasets' in g:
                self.indexed_datasets = list(g['indexed_datasets'][...])
                self.indexed_datasets_indexes = list(
                    g['indexed_datasets_indexes'][...])
                self.indexes = {}
                for dset in g['indexes']:
                    self.indexes[dset] = list(g['indexes'][dset][...])
            else:
                self.indexed_datasets = []
            if 'non_fused_datasets' in g:
                self.non_fused_datasets = list(g['non_fused_datasets'][...])
            else:
                self.non_fused_datasets = []
            if 'fused_datasets' in g:
                self.fused_datasets = list(g['fused_datasets'][...])
                self.fused_members = {}
                self.key_weights = {}
                self.nb_levels = {}
                for fused_dataset in g['fused']:
                    self.fused_members[fused_dataset] = list(
                        g['fused'][fused_dataset]['datasets'][...])
                    if fused_dataset + '/key_weights' in g['fused']:
                        self.key_weights[fused_dataset] = g['fused'][
                            fused_dataset]['key_weigths'][...]
                    else:
                        self.nb_levels[fused_dataset] = g['fused'][
                            fused_dataset]['nb_levels'][...]
            else:
                self.fused_datasets = []

    # FIXME h5io should be developed as a subclass of np2h5
    def __enter__(self):
        try:
            self.np2h5 = np2h5.NP2H5(self.filename)
            self.np2h5.__enter__()
            return self
        except:
            # FIXME if this fails might need a try block to ignore the
            # exception?
            del self.np2h5
            raise

    def __exit__(self, eType, eValue, eTrace):
        try:
            self.np2h5.__exit__(eType, eValue, eTrace)
        # FIXME here could need to ignore/log a second exception if eValue is
        # not None
        finally:
            del self.np2h5

    def write(self, data, append=True, iterate=False, indexed=False):
        if not(hasattr(self, 'np2h5')):
            raise RuntimeError(
                "Writing to h5io objects must be done inside a context manager ('with' statemt)")
        if not(self.is_empty) and not(append):
            raise IOError('File %s is already filled' % self.filename)
        # if necessary, instantiate datasets
        if self.is_empty:
            if iterate:
                sample_data = data.next()
            else:
                sample_data = data
            self.__initialize_datasets__(sample_data)
        else:
            sample_data = None
            # FIXME for now have to check that np2h5 was initialized
            if not(self.np2h5.buffers):
                raise ValueError(
                    "Current implementation does not allow to complete non-empty datasets")
        # set flags
        with h5py.File(self.filename) as f:
            if self.is_empty:
                self.is_empty = False
                f[self.group].attrs['empty'] = False
            if self.is_sorted:
                self.is_sorted = False
                f[self.group].attrs['sorted'] = False
        if not(sample_data is None) and iterate:
            self.__write__(sample_data, indexed)
        if iterate:
            for d in data:
                self.__write__(d, indexed)
        else:
            self.__write__(data, indexed)

    def __parse_input_data__(self, data):
        if not(isinstance(data, collections.Mapping)):
            data_dict = {}
            for dataset, d in zip(self.managed_datasets, data):
                data_dict[dataset] = d
            data = data_dict
        if not(set(data.keys()) == set(self.managed_datasets)):
            raise ValueError(
                'It is necessary to write to all of the managed datasets simultaneously.')
        return data

    def __convert_input_data__(self, data):
        res = {}
        for dset, d in iteritems(data):
            if not(hasattr(d, 'shape')):
                d = np.array(d)  # risky type conversion ?
            if len(d.shape) == 1:
                # to avoid shape problems, maybe non optimal
                d = np.reshape(d, (d.shape[0], 1))
            res[dset] = d
        return res

    def __initialize_datasets__(self, sample_data):
        self.out = {}
        sample_data = self.__parse_input_data__(sample_data)
        sample_data = self.__convert_input_data__(sample_data)
        dims = {dset: 1 if len(data.shape) == 1 else data.shape[
            1] for dset, data in iteritems(sample_data)}
        # needed for raw_datasets only
        dtypes = {
            dset: get_dtype(sample_data[dset]) for dset in self.raw_datasets}
        # init raw datasets
        for dset in self.raw_datasets:
            (group, dataset) = os.path.split(dset)
            if not(group):
                group = '/'
            self.out[dset] = self.np2h5.add_dataset(group, dataset, n_columns=dims[dset], item_type=dtypes[
                                                    dset], fixed_size=False)  # FIXME at some point should become super.add_dataset(...)
        # init not fused indexed datasets, in this implementation they are all
        # encoded in the same matrix
        if self.non_fused_datasets:
            indexed_dims = [dims[dset] for dset in self.non_fused_datasets]
            indexed_levels = [len(self.indexes[dset])
                              for dset in self.non_fused_datasets]
            dim = sum(indexed_dims)
            # smallest unsigned integer dtype compatible with all
            # indexed_datasets
            d_type = type_fitting.fit_integer_type(
                max(indexed_levels), is_signed=False)
            # FIXME at some point should become super.add_dataset(...)
            self.out['indexed'] = self.np2h5.add_dataset(
                self.group, 'indexed_data', n_columns=dim, item_type=d_type, fixed_size=False)
            with h5py.File(self.filename) as f:
                # necessary to access the part of the data corresponding to a
                # particular dataset
                f[self.group].create_dataset(
                    'indexed_cumudims', data=np.cumsum(indexed_dims), dtype=np.uint64)
        # fused datasets have a separate one dimensional dataset each
        self.key_weights = {}
        for fused_dset in self.fused_datasets:
            fused_dims = np.array(
                [dims[dset] for dset in self.fused_members[fused_dset]], dtype=np.uint64)
            max_key = np.prod(
                self.nb_levels[fused_dset] ** fused_dims) - np.uint64(1)
            if max_key >= 2 ** 64:
                raise ValueError('fused dataset %s in file %s cannot be created because 64 bits keys are not sufficient to cover all possible combinations of the fused datasets' % (
                    fused_dset, self.filename))
            # smallest unsigned integer dtype compatible
            d_type = type_fitting.fit_integer_type(max_key, is_signed=False)
            # FIXME at some point should become super.add_dataset(...)
            self.out[fused_dset] = self.np2h5.add_dataset(
                self.group, fused_dset, n_columns=1, item_type=d_type, fixed_size=False)
            nb_levels_with_multiplicity = np.concatenate([np.array(
                n, dtype=d_type) * np.ones(d, dtype=d_type) for n, d in zip(self.nb_levels[fused_dset], fused_dims)])
            self.key_weights[fused_dset] = np.concatenate(
                [np.array([1], dtype=d_type), np.cumprod(d_type(nb_levels_with_multiplicity))[:-1]])
            with h5py.File(self.filename) as f:
                f[self.group]['fused'][fused_dset].create_dataset(
                    'key_weights', data=self.key_weights[fused_dset], dtype=d_type)

    def __write__(self, data, indexed=False):
        data = self.__parse_input_data__(data)
        if not(indexed):
            data = self.__compute_indexes__(data)
        data = self.__convert_input_data__(data)
        # write raw data
        for dset in self.raw_datasets:
            # need type conversion sometimes here? (np.array(data[dset]))
            self.out[dset].write(data[dset])
        # write indexed data
        if self.non_fused_datasets:
            # FIXME check that values are in correct range of index ?
            indexed_values = [data[dset] for dset in self.non_fused_datasets]
            # need type conversion sometimes here?
            self.out['indexed'].write(np.concatenate(indexed_values, axis=1))
        # write fused data
        for fused_dset in self.fused_datasets:
            keys = self.__compute_keys__(fused_dset, np.concatenate(
                [data[key] for key in self.fused_members[fused_dset]], axis=1))  # need type conversion sometimes here?
            self.out[fused_dset].write(keys)

    # this function might be optimized if useful (using searchsorted and
    # stuff?)
    def __compute_indexes__(self, data):
        data = dict([(dset, [self.indexes[self.indexed_datasets_indexes[self.indexed_datasets.index(dset)]].index(
            e) for e in d]) if dset in self.indexed_datasets else (dset, d) for dset, d in iteritems(data)])
        return data

    def __compute_keys__(self, dset, values):
        d_type = self.key_weights[dset].dtype
        # this is vectorial
        keys = np.sum(
            self.key_weights[dset] * np.array(values, dtype=d_type), axis=1)
        keys = np.reshape(keys, (keys.shape[0], 1))
        return keys

    def sort(self):
        pass

    def find(self):
        pass

    def read(self):
        pass


# auxiliary function for determining dtype, strings (unicode or not) are
# always encoded with a variable length dtype, thus it should be more
# efficient in general to index string outputs, it's actually mandatory
# because determining chunk_size would fail for non-indexed strings
def get_dtype(data):
    str_dtype = h5py.special_dtype(vlen=str)
    # allow for the use of strings
    if isinstance(data[0], basestring):
        dtype = str_dtype
    # could add some checks that the dtype is one of those supported by h5 ?
    elif hasattr(data, 'dtype'):
        dtype = data.dtype
    else:
        dtype = np.array(data).dtype
    return dtype


def test_h5io():
    try:
        with H5IO('testh5io1.h5', ['talker1', 'talker2']) as h1:
            h1.write([[0, 1], [1, 2]])
            h1.write((([[i, i + 1], [10 - i, i]])
                      for i in range(5)), iterate=True)
            h1.write({'talker1': [51], 'talker2': [62]})
        with H5IO('testh5io2.h5', {'talker1': 'talker', 'talker2': 'talker', 'language': 'language', 'age1': None, 'age2': None}, {'talker': ['t1', 't2', 't3'], 'language': ['French', 'English']}, {'talkers': ['talker1', 'talker2']}) as h2:
            h2.write({'talker1': ['t1', 't2', 't2'], 'talker2': ['t3', 't3', 't3'], 'language': [
                     'French', 'English', 'French'], 'age1': [44, 33, 22], 'age2': [11, 33, 21]}, indexed=False)
            h2.write({'talker1': [0, 1, 2], 'talker2': [1, 1, 1], 'language': [
                     0, 0, 0], 'age1': [44, 33, 22], 'age2': [11, 33, 21]}, indexed=True)
    finally:
        pass
        # os.remove('testh5io1.h5')
        # os.remove('testh5io2.h5')
