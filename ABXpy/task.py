#!/usr/bin/env python
"""This module is used for creating a new task and preprocessing.

This module contains the functions to specify and initialise a new ABX
task, compute and display the statistics, and generate the ABX
triplets and pairs.

It can also be used in a command line. See task --help for the
documentation

Usage
-----

From the command line:

.. code-block:: bash

    python task.py my_data.item \
        -o column1 -a column2 column3 -b column4 column5 \
        -f "[attr == 0 for attr in column3_X]"

my_data.item is a special file containing an index of the database and
a set of labels or attributes. See input format
[here](http://abxpy.readthedocs.io/en/latest/FilesFormat.html#dataset)

In python:

.. code-block:: python

    import ABXpy.task

    # create a new task and compute the statistics
    myTask = ABXpy.task.Task(
        'data.item', 'on_label', 'across_feature', 'by_label',
        filters=my_filters, regressors=my_regressors)

    # display statistics
    print myTask.stats

    # generate a h5db file 'data.abx'containing all the triplets and pairs
    myTask.generate_triplets()


Example
-------

An example of ABX triplet:

+------+------+------+
|  A   |  B   |  X   |
+======+======+======+
| on_1 | on_2 | on_1 |
+------+------+------+
| ac_1 | ac_1 | ac_2 |
+------+------+------+
| by   | by   | by   |
+------+------+------+

A and X share the same 'on' attribute; A and B share the same 'across'
attribute; A,B and X share the same 'by' attribute

"""

import argparse
import os
import sys
import tempfile

from six import iteritems, itervalues

import h5py
import numpy as np
import pandas as pd
import tables
import warnings

import ABXpy.database.database as database
import ABXpy.h5tools.np2h5 as np2h5
import ABXpy.h5tools.h52np as h52np
import ABXpy.h5tools.h5_handler as h5_handler
import ABXpy.h5tools.h5io as h5io
import ABXpy.sampling.sampler as sampler
import ABXpy.sideop.filter_manager as filter_manager
import ABXpy.sideop.regressor_manager as regressor_manager
import ABXpy.misc.progress_display as progress_display
from ABXpy.misc.type_fitting import fit_integer_type

# FIXME many of the fixmes should be presented as feature requests in
# a github instead of fixmes
#
# FIXME get a memory and speed efficient mechanism for storing a task
# on disk and loading it back (pickling doesn't work well)
#
# FIXME filter out empty 'on-across-by' blocks and empty 'by' blocks
# as soon as possible (i.e. when computing stats)
#
# FIXME generate unique_pairs in separate file
#
# FIXME find a better scheme for naming 'by' datasets in HDF5 files
# (to remove the current warning)
#
# FIXME efficiently dealing with case where there is no across
#
# FIXME syntax to specify names for side-ops when computing them on
# the fly or at the very least number of output (default is one)
#
# FIXME implementing file locking, md5 hash and path for integrity
# checks and logging warnings using the standard logging library of
# python + a verbose stuff
#
# FIXME putting metadata in h5files + pretty print it
#
# FIXME dataset size for task file seems too big when filtering so as
# to get only 3 different talkers?
#
# FIXME allow specifying regressors and filters from within python
# using something like (which should be integrated with the existing
# dbfun stuff):
#
#   class ABX_context(object):
#       def __init__(self, db):
#           # init fields with None
#           context = ABX_context(db_file)
#       def new_filter(context):
# 	    return [True for e in context.talker_A]
#
# FIXME allow other ways of providing the hierarchical db (directly in
# pandas format, etc.)
#
# More complicated FIXMES
# -----------------------
#
# FIXME taking by datasets as the basic unit was a mistake, because
# cases where there many small by datasets happen. Find a way to group
# them when needed both in the computations and in the h5 files
#
# FIXME allow by sampling customization depending on the analyzes to
# be carried out


class Task(object):
    """Define an ABX task for a given database.

    Attributes
    ----------

    `stats` : dict. Contain several statistics about the task. The main
        3 attributes are:

    - nb_blocks the number of blocks of ABX triplets sharing the same 'on',
      'across' and 'by' features.

    - nb_triplets the number of triplets considered.

    - nb_by_levels the number of blocks of ABX triplets sharing the same
      'by' attribute.

    Parameters
    ----------

    db_name : str
        the filename of database on which the ABX task is applied.

    on : str
        the 'on' attribute of the ABX task. A and X share the same 'on'
        attribute and B has a different one.

    across : list, optional
        a list of strings containing the 'across' attributes of the ABX
        task. A and B share the same 'across' attributes and X has a
        different one.

    by : list, optional
        a list of strings containing the 'by' attributes of the ABX task. A,B
        and X share the same 'by' attributes.

    filters : list, optional
        a list of string specifying a filter on A, B or X.

    regressors : list, optional
        a list of string specifying a filter on A, B or X.

    verbose : bool, optional
        display additionnal information is set to True.

    """
    def __init__(self, db_name, on, across=None, by=None,
                 filters=None, regressors=None, verbose=False):
        # check the item file is here
        if not os.path.isfile(db_name):
            raise AssertionError('item file {} not found'.format(db_name))

        # check 'on' is a string
        if not isinstance(on, str):
            raise AssertionError('ON attribute must be specified by a string')

        # parse input arguments
        self.database = db_name
        self.verbose = verbose
        self.on = [on]
        self.across = self._init_as_list(across)
        self.by = self._init_as_list(by)

        # load the item database and check it
        self.db, self.db_hierarchy, feat_db = database.load(
            self.database, features_info=True)
        self._init_check_database()

        # if 'by' or 'across' are empty create appropriate dummy
        # columns. '#' is forbidden in user names for columns. Note
        # that this additional columns are not in the db_hierarchy,
        # but Thomas don't think this is problematic.
        if not self.by:
            self.db['#by'] = 0
            self.by = ['#by']

        if not self.across:
            self.db['#across'] = range(len(self.db))
            self.across = ['#across']

        # setup filters
        self.filters = filter_manager.FilterManager(
            self.db_hierarchy, self.on, self.across, self.by,
            [] if filters is None else filters)

        # setup regressors
        self.regressors = regressor_manager.RegressorManager(
            self.db, self.db_hierarchy, self.on, self.across, self.by,
            [] if regressors is None else regressors)

        # some other attributes that are populated during the database
        # preparation below
        self.by_dbs = {}
        self.types = {}
        self.feat_dbs = {}
        self.on_blocks = {}
        self.across_blocks = {}
        self.on_across_blocks = {}
        self.antiacross_blocks = {}

        # prepare the database for generating the triplets
        self._init_prepare_database(feat_db)
        self._init_prepare_types()

        # compute some statistics about the task
        self.compute_statistics()

    @staticmethod
    def _init_as_list(arg):
        """Helper method to load an argument as a list"""
        if arg is None:
            return []
        elif isinstance(arg, str):
            return [arg]
        else:
            return arg

    def _init_check_database(self):
        """Check the ABX database (item file)"""
        # FIXME add additional checks, for example that columns in BY,
        # ACROSS, ON are not the same ? (see task structure notes)
        # also that location columns are not used
        if self.verbose:
            print('checking input database {}'.format(self.database))

        # check that required columns are present
        cols = set(self.db.columns)
        message = (
            ' argument is invalid, check that all the provided attributes '
            'are defined in the database {}'.format(self.database))
        # the argument of issuperset needs to be a list ...
        assert cols.issuperset(self.on), 'ON' + message
        assert cols.issuperset(self.across), 'ACROSS' + message
        assert cols.issuperset(self.by), 'BY' + message

        for col in cols:
            assert '_' not in col, \
                col + ': you cannot use underscore in column names'
            assert '#' not in col, \
                col + ': you cannot use \'#\' in column names'

        if self.verbose:
            print("input database verified")

    def _init_prepare_database(self, feat_db):
        """Prepare the database for triplet generation"""
        by_groups = self.db.groupby(self.by)

        if self.verbose:
            display = progress_display.ProgressDisplay()
            display.add('block', 'Preprocessing by block', len(by_groups))

        for by_key, by_frame in by_groups:
            if self.verbose:
                display.update('block', 1)
                display.display()

            # allow to get by values as well as values of other variables
            # that are determined by these
            by_values = dict(by_frame.iloc[0])

            # apply 'by' filters
            if self.filters.by_filter(by_values):
                # get analogous feat_db
                by_feat_db = feat_db.iloc[by_frame.index]

                # drop indexes
                by_frame = by_frame.reset_index(drop=True)

                # reset_index to get an index relative to the 'by' db,
                # the original index could be conserved in an additional
                # 'index' column if necessary by removing the drop=True, but
                # this would add another constraint on the possible column name
                by_feat_db = by_feat_db.reset_index(drop=True)

                # apply generic filters
                by_frame = self.filters.generic_filter(by_values, by_frame)

                self.by_dbs[by_key] = by_frame
                self.feat_dbs[by_key] = by_feat_db

                def _by_dbs(l): return self.by_dbs[by_key].groupby(l)
                self.on_blocks[by_key] = _by_dbs(self.on)
                self.across_blocks[by_key] = _by_dbs(self.across)
                self.on_across_blocks[by_key] = _by_dbs(self.on + self.across)

                if len(self.across) > 1:
                    self.antiacross_blocks[by_key] = dict()
                    for across_key in self.across_blocks[by_key].groups:
                        b = True
                        for i, col in enumerate(self.across):
                            b = b * (by_frame[col] != across_key[i])
                        self.antiacross_blocks[by_key][across_key] = (
                            by_frame[b].index)

    def _init_prepare_types(self):
        """Determining appropriate numeric type to represent index

        Currently used only for numpy arrays and h5 storage, might
        also be used for panda frames.

        """
        # len(db)-1 wouldn't work here because there could be missing
        # index due to generic filtering
        self.types = {
            key: fit_integer_type(np.max(db.index.values), is_signed=False)
            for key, db in iteritems(self.by_dbs)}

    def compute_statistics(self, approximate=False):
        """Compute the statistics of the task

        The number of ABX triplets is exact in most cases if approximate is
        set to false. The other statistics can only be approxrimate in the case
        where there are A, B, X or ABX filters.

        Parameters
        ----------

        approximate : bool
            approximate the number of triplets

        """
        self.stats = {}
        self.stats['approximate'] = bool(self.filters.A or self.filters.B or
                                         self.filters.X or self.filters.ABX)
        self.stats['approximate_nb_triplets'] = approximate and self.stats[
            'approximate']
        self.stats['nb_by_levels'] = len(self.by_dbs)
        self.by_stats = {}

        if self.verbose:
            display = progress_display.ProgressDisplay()
            display.add('block', 'Computing statistics for by block',
                        self.stats['nb_by_levels'])

        for by in self.by_dbs:
            if self.verbose:
                display.update('block', 1)
                display.display()

            stats = {}
            stats['nb_items'] = len(self.by_dbs[by])
            stats['on_levels'] = self.on_blocks[by].size()
            stats['nb_on_levels'] = len(stats['on_levels'])
            stats['across_levels'] = self.across_blocks[by].size()
            stats['nb_across_levels'] = len(stats['across_levels'])
            stats['on_across_levels'] = self.on_across_blocks[by].size()
            stats['nb_on_across_levels'] = len(stats['on_across_levels'])
            self.by_stats[by] = stats

        self.stats['nb_blocks'] = sum(
            [bystats['nb_on_across_levels']
             for bystats in self.by_stats.values()])

        if self.verbose:
            display = progress_display.ProgressDisplay()
            display.add(
                'block', 'Computing statistics for by/on/across block',
                self.stats['nb_blocks'])

        for by, db in iteritems(self.by_dbs):
            stats = self.by_stats[by]
            stats['block_sizes'] = {}
            stats['nb_triplets'] = 0
            stats['nb_across_pairs'] = 0
            stats['nb_on_pairs'] = 0

            # iterate over on/across blocks
            for block_key, count in iteritems(stats['on_across_levels']):
                if self.verbose:
                    display.update('block', 1)
                    display.display()

                block = self.on_across_blocks[by].groups[block_key]
                on_across_by_values = dict(db.iloc[block[0]])

                # retrieve the on and across keys (as they are stored
                # in the panda object)
                on, across = on_across_from_key(block_key)

                # apply the filter and check if block is empty
                if self.filters.on_across_by_filter(on_across_by_values):
                    n_A = count
                    n_X = stats['on_levels'][on]

                    # FIXME quick fix to process case whith no across, but
                    # better done in a separate loop ...
                    if self.across == ['#across']:
                        n_B = stats['nb_items'] - n_X
                    else:
                        n_B = stats['across_levels'][across] - n_A

                    n_X = n_X - n_A
                    stats['nb_across_pairs'] += n_A * n_B
                    stats['nb_on_pairs'] += n_A * n_X

                    need_approx = approximate or not(
                        self.filters.A or self.filters.B
                        or self.filters.X or self.filters.ABX)

                    if need_approx and not isinstance(across, tuple):
                        stats['nb_triplets'] += n_A * n_B * n_X
                        stats['block_sizes'][block_key] = n_A * n_B * n_X
                    else:
                        # count exact number of triplets, could be further
                        # optimized because it isn't necessary to do the whole
                        # triplet generation, in particular in the case where
                        # there are no ABX filters
                        nb_triplets = self.on_across_triplets(
                            by, on, across, block, on_across_by_values,
                            with_regressors=False).shape[0]

                        stats['nb_triplets'] += nb_triplets
                        stats['block_sizes'][block_key] = nb_triplets
                else:
                    stats['block_sizes'][block_key] = 0

        self.stats['nb_triplets'] = sum(
            [bystats['nb_triplets'] for bystats in self.by_stats.values()])

        # FIXME remove empty by blocks then remove empty on_across_by
        # blocks here, also reset self.n_blocks in consequence
        self.n_blocks = self.stats['nb_blocks']

    def on_across_triplets(self, by, on, across,
                           on_across_block, on_across_by_values,
                           with_regressors=True):
        """Generate all possible triplets for a given by block.

        Given an on_across_block of the database and the parameters of the
        task, this function will generate the complete set of triplets and
        the regressors.

        Parameters
        ----------

        by : int
            The block index

        on, across : int
            The task attributes

        on_across_block : list
            the block

        on_across_by_values : dict
            the actual values

        with_regressors : bool, optional
            By default, true

        Returns
        -------

        triplets : numpy.Array
            the set of triplets generated

        regressors : numpy.Array
            the regressors generated

        """
        # find all possible A, B, X where A and X have the 'on'
        # feature of the block and A and B have the 'across' feature
        # of the block
        A = np.array(on_across_block, dtype=self.types[by])
        on_set = set(self.on_blocks[by].groups[on])

        # FIXME quick fix to process case with no across, but better
        # done in a separate loop...
        if self.across == ['#across']:
            # in this case A is a singleton and B can be anything in
            # the by block that doesn't have the same 'on' as A
            B = np.array(
                list(set(self.by_dbs[by].index).difference(on_set)),
                dtype=self.types[by])
        else:
            # remove B with the same 'on' than A
            B = np.array(
                list(set(self.across_blocks[by].groups[across]).difference(A)),
                dtype=self.types[by])

        # remove X with the same 'across' than A
        if type(across) is tuple:
            antiacross_set = set(self.antiacross_blocks[by][across])
            X = np.array(list(antiacross_set & on_set), dtype=self.types[by])
        else:
            X = np.array(list(on_set.difference(A)), dtype=self.types[by])

        # apply singleton filters
        db = self.by_dbs[by]
        if self.filters.A:
            iA = self.filters.A_filter(on_across_by_values, db, A)
            A = A[iA]
        if self.filters.B:
            iB = self.filters.B_filter(on_across_by_values, db, B)
            B = B[iB]
        if self.filters.X:
            iX = self.filters.X_filter(on_across_by_values, db, X)
            X = X[iX]

        # instantiate A, B, X regressors here
        if with_regressors:
            self.regressors.set_A_regressors(on_across_by_values, db, A)
            self.regressors.set_B_regressors(on_across_by_values, db, B)
            self.regressors.set_X_regressors(on_across_by_values, db, X)

        # A, B, X can then be combined efficiently in a full (or
        # randomly sampled) factorial design
        size = len(A) * len(B) * len(X)
        on_across_block_index = [0]

        if size > 0:
            ind_type = fit_integer_type(size, is_signed=False)
            indices = np.arange(size, dtype=ind_type)

            # generate triplets from indices
            iX = np.mod(indices, len(X))
            iB = np.mod(np.floor_divide(indices, len(X)), len(B))
            iA = np.floor_divide(indices, len(B) * len(X))
            triplets = np.column_stack((A[iA], B[iB], X[iX]))

            # apply triplets filters
            if self.filters.ABX:
                ABX_filter_ind = self.filters.ABX_filter(
                    on_across_by_values, db, triplets)
                triplets = triplets[ABX_filter_ind]
                size = triplets.shape[0]

            if with_regressors:
                # If I understand correctly, this is supposed to first
                # give a unique id to each combination of regressors
                # and then sort the triplets so as to have triplets
                # with the same combination of regressors next to each
                # other.  Is the on_across_block_index created ever
                # reused for allowing indexed and thus more efficient
                # access in later procesing (e.g. in analyze.py) or is
                # it only for thresholding ?

                # reindexing by regressors
                Breg = [reg[iB] for regs in self.regressors.B_regressors
                        for reg in regs]

                Xreg = [reg[iX] for regs in self.regressors.X_regressors
                        for reg in regs]

                if self.filters.ABX:
                    Breg = [reg[ABX_filter_ind] for reg in Breg]
                    Xreg = [reg[ABX_filter_ind] for reg in Xreg]

                regs = np.array(Breg + Xreg).T
                if len(regs) != 0:
                    n_regs = np.max(regs, 0) + 1

                    # FIXME how do we know that all regressors are in
                    # integer format here ? This is only guaranteed
                    # for indexed regressors...
                    assert np.prod(n_regs) < 18446744073709551615, \
                        "type not big enough"

                    reg_ind_type = fit_integer_type(
                        np.prod(n_regs), is_signed=False)

                    new_index = regs[:, 0].astype(reg_ind_type)
                    for i in range(1, len(n_regs)):
                        new_index = regs[:, i] + n_regs[i] * new_index

                    permut = np.argsort(new_index)

                    # the organization should be revamped: the real
                    # sorting is done by the line just above, while
                    # the 'sort_and_threshold' function is only really
                    # doing something when thresholding, otherwise it
                    # is just generating the on_across_block_index
                    # which would be better done in another
                    # function...
                    thr_sort_permut, on_across_block_index = (
                        sort_and_threshold(
                            permut, new_index, reg_ind_type,
                            threshold=self.threshold))
                    triplets = triplets[thr_sort_permut]
                else:
                    # FIXME was a bug breaking tests -> variable need
                    # to be defined
                    thr_sort_permut = np.empty(shape=0, dtype=np.uint8)

        else:
            # empty block...
            triplets = np.empty(shape=(0, 3), dtype=self.types[by])

            # the following lines assign empty values to all the
            # variables used to set regressors. Would be nicer to let
            # the regressor code detect empty triplets and handle it
            # by itself... (it is useless if not(with_regressors)
            iA = np.empty(shape=0, dtype=np.uint8)
            iB = np.empty(shape=0, dtype=np.uint8)
            iX = np.empty(shape=0, dtype=np.uint8)

            if self.filters.ABX:
                ABX_filter_ind = np.empty(shape=0, dtype=np.uint8)

            thr_sort_permut = np.empty(shape=0, dtype=np.uint8)

        if not with_regressors:
            return triplets
        else:
            if self.regressors.ABX:
                # instantiate ABX regressors here
                self.regressors.set_ABX_regressors(
                    on_across_by_values, db, triplets)

            # make sure we have those variables defined
            try:
                ABX_filter_ind
            except NameError:
                ABX_filter_ind = None

            # compute the task regressors
            regressors = self._compute_regressors(
                triplets, iA, iB, iX, ABX_filter_ind, thr_sort_permut)

            return (triplets,
                    regressors,
                    np.array(on_across_block_index)[:, None])

    # FIXME add a mechanism to allow the specification of a random seed in a
    # way that would produce reliably the same triplets on different machines
    # (means cross-platform random number generator + having its state so as
    # to be sure that no other random number generation calls to it are
    # altering the sequence).
    #
    # FIXME use an object that guarantees that the stream will not be
    # perturbed by external codes calls to np.random.
    def generate_triplets(self, output=None,
                          threshold=None, tmpdir=None, seed=None):
        """Generate all possible triplets for the whole task

        Generate the triplets and the pairs for an ABXpy.Task and
        store it in a h5db file.

        Parameters
        ----------

        output : filename, optional
            The output file. If not specified, it will automatically
            create a new file with the same name as the input file.

        threshold : TODO

        tmpdir : directory, optional
           where to write temporary files

        seed : int, optional
           seed for initializing the random number generator

        """
        # reinitialize the random generator with the provided seed
        # (TODO this is only used for sampling, so it should be moved
        # out during code refactoring -> put that in main(), or in
        # sampling module?)
        np.random.seed(seed)

        # check we have triplets in the database
        if self.stats['nb_triplets'] == 0:
            warnings.warn('There are no possible ABX triplets'
                          ' in the specified task', UserWarning)
            return
        self.total_n_triplets = self.stats['nb_triplets']

        # setup threshold
        self.threshold = threshold if threshold is not None else False

        # setup output file, raise an error if the file already exists
        if output is None:
            output = os.path.splitext(self.database)[0] + '.abx'
        if os.path.exists(output):
            raise ValueError(
                'The output file already exists: {}'.format(output))
        if self.verbose:
            print('writing output to {}'.format(output))

        self.n_triplets = self.total_n_triplets

        display = None
        if self.verbose:
            display = progress_display.ProgressDisplay()
            display.add(
                'block', 'Computing triplets for by/on/across block',
                self.n_blocks)
            display.add(
                'triplets', 'Triplets considered:', self.total_n_triplets)

        by_block_indices = [0]
        self.current_index = 0

        # fill output file with list of needed ABX triplets, it is done
        # independently for each 'by' value
        with np2h5.NP2H5(h5file=output) as fh:
            # FIXME test if not fixed size impacts performance a lot
            out = fh.add_dataset(
                group='triplets',
                dataset='data',
                n_rows=self.n_triplets,
                n_columns=3,
                item_type=fit_integer_type(self.total_n_triplets),
                fixed_size=False)

            out_block_index = fh.add_dataset(
                group='triplets',
                dataset='on_across_block_index',
                n_rows=self.stats['nb_blocks'],
                n_columns=1,
                item_type=fit_integer_type(self.stats['nb_blocks']),
                fixed_size=False)

            empty_by_blocks = []
            bys = []
            for by, db in iteritems(self.by_dbs):
                # class for efficiently writing to datasets of the output file
                # (using a buffer under the hood)
                if self.verbose:
                    print("Writing ABX triplets to task file...")

                # allow to get by values as well as values of other
                # variables that are determined by these
                by_values = dict(db.iloc[0])

                datasets, indexes = self.regressors.get_regressor_info()
                with h5io.H5IO(
                        filename=output,
                        datasets=datasets,
                        indexes=indexes,
                        group='/regressors/{}/'.format(str(by))) as out_regs:
                    self._compute_triplets(
                        by, out, out_block_index, out_regs, db, fh,
                        by_values, display=display)

                    # if no triplets found: delete by block
                    if self.current_index == by_block_indices[-1]:
                        empty_by_blocks.append(by)
                    else:
                        by_block_indices.append(self.current_index)
                        bys.append(by)

            # saving by index, deleting empty by blocks:
            aux = np.array(
                by_block_indices,
                dtype=fit_integer_type(by_block_indices[-1]))
            by_block_indices = np.hstack((aux[:-1, None], aux[1:, None]))
            for by in empty_by_blocks:
                del self.by_dbs[by]

            fh.file.create_dataset(
                'bys', (aux.shape[0] - 1,),
                dtype=h5py.special_dtype(vlen=str))
            fh.file['bys'][:] = [str(by) for by in bys]

            fh.file['triplets'].create_dataset(
                'by_index', data=by_block_indices)
            fh.file['triplets/data'].resize(aux[-1], axis=0)

        if self.verbose:
            print('done.')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', tables.NaturalNameWarning)
            self._generate_pairs(output, tmpdir=tmpdir)

    def _compute_triplets(self, by, out, out_block_index,
                          out_regs, db, fh, by_values, display=None):
        # instantiate by regressors here
        self.regressors.set_by_regressors(by_values)

        # iterate over on/across blocks
        on_across_blocks = iteritems(self.on_across_blocks[by].groups)
        for block_key, block in on_across_blocks:
            if self.verbose:
                display.update('block', 1)

            # allow to get on, across, by values as well as values of
            # other variables that are determined by these
            on_across_by_values = dict(db.iloc[block[0]])
            if self.filters.on_across_by_filter(on_across_by_values):
                # instantiate on_across_by regressors here
                self.regressors.set_on_across_by_regressors(
                    on_across_by_values)

                on, across = on_across_from_key(block_key)

                triplets, regressors, on_across_block_index = (
                    self.on_across_triplets(
                        by, on, across, block, on_across_by_values))

                out.write(triplets)
                out_regs.write(regressors, indexed=True)
                out_block_index.write(on_across_block_index)
                self.current_index += triplets.shape[0]

                if self.verbose:
                    display.update(
                        'triplets',
                        self.by_stats[by]['block_sizes'][block_key])

            if self.verbose:
                display.display()

    # FIXME clean this function (maybe do a few well-separated sub-functions
    # for getting the pairs and unique them)
    def _generate_pairs(self, output=None, tmpdir=None):
        """Generate the pairs associated to the triplet list"""

        # FIXME change this to a random file name to avoid overwriting problems
        # default name for output file
        if output is None:
            (basename, _) = os.path.splitext(self.database)
            output = basename + '.abx'
        # list all pairs
        n_pairs_dict = {}
        max_ind_dict = {}
        try:
            _, output_tmp = tempfile.mkstemp(dir=tmpdir)
            for n_by, (by, db) in enumerate(iteritems(self.by_dbs)):
                if self.verbose > 0:
                    print("Writing AX/BX pairs to task file...")
                with h5py.File(output, 'a') as fh:
                    triplets_attrs = fh['/triplets']['by_index'][n_by][...]
                max_ind = np.max(db.index.values)
                max_ind_dict[by] = max_ind
                pair_key_type = fit_integer_type(
                    (max_ind + 1) ** 2 - 1, is_signed=False)
                with h52np.H52NP(output) as f_in:
                    with np2h5.NP2H5(output_tmp) as f_out:
                        inp = f_in.add_subdataset('triplets', 'data',
                                                  indexes=triplets_attrs)
                        out = f_out.add_dataset(
                            'pairs', str(by), n_columns=1,
                            item_type=pair_key_type, fixed_size=False)
                        for data in inp:
                            triplets = pair_key_type(data)
                            n = triplets.shape[0]
                            ind = np.arange(n)
                            i1 = 2 * ind
                            i2 = 2 * ind + 1

                            pairs = np.empty(
                                shape=(2 * n, 1),
                                dtype=pair_key_type)

                            # FIXME change the encoding (and type_fitting)
                            # so that A,B and B,A have the same code ...
                            # (take a=min(a,b), b=max(a,b))
                            # FIXME but allow a flag to control the
                            # behavior to be able to enforce A,X and B,X
                            # order when using assymetrical distance
                            # functions
                            pairs[i1, 0] = triplets[:, 0] + (
                                max_ind + 1) * triplets[:, 2]  # AX
                            pairs[i2, 0] = triplets[:, 1] + (
                                max_ind + 1) * triplets[:, 2]  # BX

                            # FIXME do a unique here already? Do not store
                            # the inverse mapping ? (could sort triplets on
                            # pair1, complete pair1, sort on pair2,
                            # complete pair 2 and shuffle ?)
                            out.write(pairs)

                    sort_pairs(output_tmp, by, tmpdir=tmpdir)

                    # counting unique
                    with np2h5.NP2H5(output_tmp) as f_out:
                        with h52np.H52NP(output_tmp) as f_in:
                            inp = f_in.add_dataset('pairs', str(by))
                            n_pairs = 0
                            last = -1
                            for pairs in inp:
                                # unique alters the shape
                                pairs = np.reshape(pairs, (pairs.shape[0], 1))
                                n_pairs += np.unique(pairs).size
                                if pairs[0, 0] == last:
                                    n_pairs -= 1
                                if pairs.size > 0:
                                    last = pairs[-1, 0]
                        n_pairs_dict[by] = n_pairs

                    # FIXME should have a unique function directly instead of
                    # sorting + unique ?
                    with np2h5.NP2H5(output_tmp) as f_out:
                        with h52np.H52NP(output_tmp) as f_in:
                            inp = f_in.add_dataset('pairs', str(by))
                            out = f_out.add_dataset(
                                'unique_pairs', str(by),
                                n_rows=n_pairs,
                                n_columns=1,
                                item_type=pair_key_type,
                                fixed_size=False)

                            # out = out_unique_pairs
                            last = -1
                            for pairs in inp:
                                pairs = np.unique(pairs)
                                # unique alters the shape
                                pairs = np.reshape(pairs, (pairs.shape[0], 1))
                                if pairs[0, 0] == last:
                                    pairs = pairs[1:]
                                if pairs.size > 0:
                                    last = pairs[-1, 0]
                                    out.write(pairs)

                        # store for ulterior decoding
                        store = pd.HDFStore(output)

                        # use append to make use of table format,
                        # which is better at handling strings without
                        # much space (fixed-size format)
                        store.append('/feat_dbs/' + str(by), self.feat_dbs[by],
                                     expectedrows=len(self.feat_dbs[by]))
                        store.close()
                        # FIXME generate inverse mapping to triplets
                        # (1 and 2) ?

            # Now merge all datasets
            by_index = 0
            with np2h5.NP2H5(output) as f_out:
                n_rows = sum(itervalues(n_pairs_dict))
                out_unique_pairs = f_out.add_dataset(
                    'unique_pairs', 'data', n_rows=n_rows, n_columns=1,
                    item_type=np.int64, fixed_size=False)
                for n_by, (by, db) in enumerate(iteritems(self.by_dbs)):
                    triplets_attrs = f_out.file['/triplets']['by_index'][n_by]
                    if triplets_attrs[0] == triplets_attrs[1]:
                        # subdataset is empty
                        continue

                    with h52np.H52NP(output_tmp) as f_in:
                        inp = f_in.add_dataset('unique_pairs', str(by))
                        for pairs in inp:
                            out_unique_pairs.write(pairs)

                    with h5py.File(output, 'a') as fh:
                        fh['/unique_pairs'].attrs[str(by)] = (
                            max_ind_dict[by] + 1,
                            by_index, by_index + n_pairs_dict[by])
                    by_index += n_pairs_dict[by]
        finally:
            os.remove(output_tmp)
        if self.verbose:
            print("done.")

    # number of triplets when triplets with same on, across, by are
    # counted as one
    #
    # FIXME current implementation won't work with A, B, X or ABX filters
    #
    # FIXME lots of code in this function is repicated from
    # on_across_triplets, generate_triplets and/or compute_stats: the
    # maximum possible should be factored out, including the loop over
    # by, loop over on_across iteration structure
    def compute_nb_levels(self):
        if self.filters.A or self.filters.B or self.filters.X or \
           self.filters.ABX:
            raise ValueError(
                'Current implementation do not support computing nb_levels in '
                'the presence of A, B, X, or ABX filters')

        if self.verbose:
            display = progress_display.ProgressDisplay()
            display.add(
                'block', 'Computing nb_levels for by block',
                self.stats['nb_by_levels'])

        for by, db in iteritems(self.by_dbs):
            if self.verbose:
                display.update('block', 1)
                display.display()

            n = 0
            # iterate over on/across blocks
            for block_key, n_block in (
                    iteritems(self.by_stats[by]['on_across_levels'])):
                block = self.on_across_blocks[by].groups[block_key]
                on_across_by_values = dict(db.ix[block[0]])
                on, across = on_across_from_key(block_key)

                if self.filters.on_across_by_filter(on_across_by_values):
                    # find all possible A, B, X where A and X have the 'on'
                    # feature of the block and A and B have the 'across'
                    # feature of the block
                    A = np.array(
                        self.on_across_blocks[by].groups[block_key],
                        dtype=self.types[by])
                    X = self.on_blocks[by].groups[on]

                    # FIXME quick fix to process case whith no across, but
                    # better done in a separate loop ...
                    if self.across == ['#across']:
                        # in this case A is a singleton and B can be anything
                        # in the by block that doesn't have the same 'on' as A
                        B = np.array(
                            list(set(self.by_dbs[by].index).difference(X)),
                            dtype=self.types[by])
                    else:
                        B = self.across_blocks[by].groups[across]

                        # remove B with the same 'on' than A
                        B = np.array(
                            list(set(B).difference(A)), dtype=self.types[by])

                    # remove X with the same 'across' than A
                    X = np.array(
                        list(set(X).difference(A)), dtype=self.types[by])

                    if B.size > 0 and X.size > 0:
                        # case were there was no across specified is different
                        if self.across == ["#across"]:
                            grouping = self.on
                        else:
                            grouping = self.on + self.across

                        n_level_B = len(db.iloc[B].groupby(grouping).groups)
                        n_level_X = len(db.iloc[X].groupby(grouping).groups)
                        n = n + n_level_B * n_level_X

            self.by_stats[by]['nb_levels'] = n

        self.stats['nb_levels'] = sum(
            stats['nb_levels'] for stats in self.by_stats.values())

    def print_stats(self, filename=None, summarized=True):
        if filename is None:
            self.print_stats_to_stream(sys.stdout, summarized)
        else:
            with open(filename, 'w') as h:
                self.print_stats_to_stream(h, summarized)

    def print_stats_to_stream(self, stream, summarized):
        import pprint

        stream.write('\n\n###### Global stats ######\n\n')
        pprint.pprint(self.stats, stream)

        stream.write('\n\n###### by blocks stats ######\n\n')
        if not(summarized):
            for by, stats in iteritems(self.by_stats):
                stream.write('### by level: %s ###\n' % str(by))
                pprint.pprint(stats, stream)
        else:
            try:
                self.compute_nb_levels()
            except ValueError:
                warnings.warn(
                    "Filters not fully supported, nb_levels per "
                    "by block wont be calculated", RuntimeWarning)

            for by, stats in iteritems(self.by_stats):
                stream.write('### by level: %s ###\n' % str(by))
                stream.write('nb_triplets: %d\n' % stats['nb_triplets'])

                if 'nb_levels' in stats:
                    stream.write('nb_levels: %d\n' % stats['nb_levels'])

                stream.write(
                    'nb_across_pairs: %d\n' % stats['nb_across_pairs'])
                stream.write(
                    'nb_on_pairs: %d\n' % stats['nb_on_pairs'])
                stream.write(
                    'nb_on_levels: %d\n' % stats['nb_on_levels'])
                stream.write(
                    'nb_across_levels: %d\n' % stats['nb_across_levels'])
                stream.write(
                    'nb_on_across_levels: %d\n' % stats['nb_on_across_levels'])

    def _compute_regressors(self, triplets, iA, iB, iX,
                            ABX_filter_ind, thr_sort_permut):
        """Helper method for Task.on_across_triplets"""
        # self.regressors.XXX contains either (for by and on_across_by)
        #   [[scalar_output_1_dbfun_1, scalar_output_2_dbfun_1,...],
        #    [scalar_output_1_dbfun_2, ...], ...]
        # or:
        #   [[np_array_output_1_dbfun_1, np_array_output_2_dbfun_1,...],
        #    [np_array_output_1_dbfun_2, ...], ...]
        #
        # FIXME change manager API so that self.regressors.A contains the
        # data and not the list of dbfun_s ?
        regressors = {}

        scalar_names = (
            self.regressors.by_names + self.regressors.on_across_by_names)
        scalar_regressors = (
            self.regressors.by_regressors
            + self.regressors.on_across_by_regressors)
        for names, regs in zip(scalar_names, scalar_regressors):
            for name, reg in zip(names, regs):
                regressors[name] = np.tile(
                    np.array(reg), (np.size(triplets, 0), 1))

        # lots of code duplication below...
        for names, regs in zip(self.regressors.A_names,
                               self.regressors.A_regressors):
            for name, reg in zip(names, regs):
                regressors[name] = reg[iA]
                if self.filters.ABX:
                    regressors[name] = regressors[name][ABX_filter_ind]
                    regressors[name] = regressors[name][thr_sort_permut]

        for names, regs in zip(self.regressors.B_names,
                               self.regressors.B_regressors):
            for name, reg in zip(names, regs):
                regressors[name] = reg[iB]
                if self.filters.ABX:
                    regressors[name] = regressors[name][ABX_filter_ind]
                regressors[name] = regressors[name][thr_sort_permut]

        for names, regs in zip(self.regressors.X_names,
                               self.regressors.X_regressors):
            for name, reg in zip(names, regs):
                regressors[name] = reg[iX]
                if self.filters.ABX:
                    regressors[name] = regressors[name][ABX_filter_ind]
                regressors[name] = regressors[name][thr_sort_permut]

        # FIXME implement this
        # for names, regs in zip(self.regressors.ABX_names,
        #                       self.regressors.ABX_regressors):
        #    for name, reg in zip(names, regs):
        #        regressors[name] = reg[indices,:]

        return regressors


# utility function necessary because of current inconsistencies in panda:
# you can't seem to index a dataframe with a tuple with only one element,
# even though tuple with more than one element are fine
def on_across_from_key(key):
    on = key[0]
    # if panda was more consistent we could use key[:1] instead ...
    across = key[1:]
    if len(across) == 1:  # this is the problematic case
        across = across[0]
    return on, across


def sort_and_threshold(permut, new_index, ind_type,
                       threshold=None, count_only=False):
    sorted_index = new_index[permut]
    flag = np.concatenate(
        ([True], sorted_index[1:] != sorted_index[:-1], [True]))
    unique_idx = np.nonzero(flag)[0]
    counts = unique_idx[1:] - unique_idx[:-1]

    if count_only:
        sampled = counts > threshold
        return new_index.shape[0] - np.sum(counts[sampled]) + \
            threshold * np.sum(sampled)

    new_permut = []
    i = 0
    for c in counts:
        if threshold and c > threshold:
            sampled_idx = sampler.sample_without_replacement(
                threshold, c, dtype=ind_type)
            sampled_idx += i
            new_permut.append(permut[sampled_idx])
        else:
            new_permut.append(permut[i:i+c])
        i += c
    return np.concatenate(new_permut), unique_idx


def sort_pairs(abx_file, by, memory=1000, tmpdir=None):
    """Sort pairs in a ABX task file

    abx_file: the hdf5 file generated by ABX task

    by:

    memory: available RAM in Mo

    tmpdir: dircetory to write temporary files

    """
    # estimate of the amount of data to be sorted
    with h5py.File(abx_file, 'a') as fh:
        n = fh['/pairs/' + str(by)].shape[0]
        i = fh['/pairs/' + str(by)].dtype.itemsize

    # harmonize units in Ko
    memory = 1000 * memory
    amount = n * i / 1000.

    # be conservative: aim at using no more than 3/4 the available
    # memory if enough memory take one chunk (this will do an
    # unnecessary full write and read of the file... could be
    # optimized easily, would it be beneficial to have large
    # o_buffer_size as well?)
    if amount <= 0.75 * memory:
        buffer_size = amount

    # else take around 30 chunks if possible (this seems efficient
    # given the current implem, using a larger number of chunks
    # efficiently might be possible if the reading chunks part of the
    # sort was cythonized ?)
    elif amount / 30. <= 0.75 * memory:
        buffer_size = amount / 30.

    # else take minimum number of chunks possible given the
    # available RAM
    else:
        buffer_size = 0.75 * memory

    # finally sort the pairs in place
    handler = h5_handler.H5Handler(abx_file, '/pairs/', str(by))
    handler.sort(buffer_size=buffer_size, tmpdir=tmpdir)


def parse_arguments():
    """Defines and parses input arguments for the command-line API"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''ABX task specification

  'database' is a text file with the '.item' extension containing an
  index of the database and a set of labels or attributes. See input
  format specifications at
  http://abxpy.readthedocs.io/en/latest/FilesFormat.html#dataset

  The --on, --across, --by, --filters and --regressors arguments must
  be defined as columns in the database (e.g. speaker or phonemes, if
  your database contains columns defining these attributes)

Example call:

  task.py ./my_data.item -o column1 -a column2 column3 -b column4 column5 \\
      -f "[attr == 0 for attr in column3_X]"

  Because optional arguments can have various numbers of inputs, the
  positional arguments ('database' and 'output') must come before the
  mandatory ones, one being preceded by '--'. Thus, those two calls
  are equivalent:

    task.py ./my_data.item -o column1 -a column2 column3
    task.py -o column1 -a column2 column3 -- ./my_data.item''')

    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='output messages to the standard output')

    parser.add_argument(
        '--stats-only', action='store_true',
        help='add this flag if you only want some statistics '
        'about the specified task')

    parser.add_argument(
        '--tempdir', default=None,
        help='directory where temporary files will be stored')

    parser.add_argument(
        '--seed', default=None, type=int,
        help='seed used to initialize the pseudo-random number generator')

    # I/O files
    g1 = parser.add_argument_group('I/O files')
    g1.add_argument(
        'database', help='database item file used to form ABX triplets')

    g1.add_argument(
        'output', nargs='?', default=None,
        help='file to write the generated ABX task, '
        'default to the database basename with the \'.abx\' extension')

    # Task specification
    g2 = parser.add_argument_group('Task specification')

    g2.add_argument(
        '-o', '--on', required=True, help='ON attribute')

    g2.add_argument(
        '-a', '--across',  nargs='+', default=[],
        help='ACROSS attributes')

    g2.add_argument(
        '-b', '--by', nargs='+', default=[],
        help='BY attributes')

    g2.add_argument(
        '-f', '--filters', nargs='+', default=[],
        help='filters specification')

    g2.add_argument(
        '-r', '--regressors', nargs='+', default=[],
        help='regressors specification')

    g2.add_argument(
        '-t', '--threshold', default=None, type=int,
        help='threshold on the maximal size of a block of'
        ' triplets sharing the same regressors')

    return parser.parse_args()


def main():
    """Command-line API for generating ABX tasks"""
    # get arguments from command line
    args = parse_arguments()

    # checks on the output file
    # if args.stats_only:
    #     assert args.output, "The output file was not provided"
    if args.output and os.path.exists(args.output):
        warnings.warn("Overwriting task file " + args.output, UserWarning)
        os.remove(args.output)

    # initialize the task
    task = Task(
        args.database, args.on,
        across=args.across,
        by=args.by,
        filters=args.filters,
        regressors=args.regressors,
        verbose=args.verbose)

    if args.stats_only:
        task.print_stats()
    else:
        if args.tempdir and not os.path.exists(args.tempdir):
            os.makedirs(args.tempdir)

        # generate triplets and unique pairs
        task.generate_triplets(
            output=args.output,
            threshold=args.threshold,
            tmpdir=args.tempdir,
            seed=args.seed)


if __name__ == '__main__':
    main()
