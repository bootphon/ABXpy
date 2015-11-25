"""This module allows to specify, initialize and preprocess an ABX task.

This module contains the functions to specify and initialize a new ABX task,
compute and display the statistics, and generate the ABX triplets and pairs.

Usage
-----

my_data.item is a special file containing an index of the database and a set
of labels or attributes. See input format [#TODO insert hypertext]

In python:

.. code-block:: python

    import ABXpy.task

    # create a new task and compute the statistics
    myTask = ABXpy.task.Task('my_data.item', 'on_label', 'across_feature', \
'by_label', filters=my_filters, regressors=my_regressors)

    # display statistics
    print myTask.stats

    # generate a h5db file 'data.abx'containing all the triplets and pairs
    myTask.generate_triplets()

Example
-------

# TODO this example is for the front page or ABX module, to move
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
attribute; A,B and X share the same 'by' attribute.

"""

import h5py
import logging
import numpy as np
import os
import pandas as pd
import pprint
import sys
from tables import NaturalNameWarning
import tempfile
import warnings

import ABXpy.database.database as abx_database
import ABXpy.h5tools.np2h5 as np2h5
import ABXpy.h5tools.h52np as h52np
import ABXpy.h5tools.h5_handler as h5_handler
import ABXpy.h5tools.h5io as h5io
import ABXpy.misc.progress_display as progress_display
import ABXpy.misc.type_fitting as type_fitting
import ABXpy.sampling.sampler as sampler
import ABXpy.sideop.filter_manager as filter_manager
import ABXpy.sideop.regressor_manager as regressor_manager


class Task(object):
    """Define an ABX task for a given database.

    Attributes:

    `stats` : dict. Contain several statistics about the task. The main \
        3 attributes are:

    - nb_blocks the number of blocks of ABX triplets sharing the same 'on', \
    'across' and 'by' features.
    - nb_triplets the number of triplets considered.
    - nb_by_levels the number of blocks of ABX triplets sharing the same \
    'by' attribute.

    """

    def __init__(self, db_file, on, across=[], by=[],
                 filters=[], regressors=[]):
        """Initialize an ABX task with the provided attributes.

        Parameters

        db_file : str
            the filename of database on which the ABX task is applied.

        on : str
            the 'on' attribute of the ABX task. A and X share the same
            'on' attribute and B has a different one.

        across : list, optional
            a list of strings containing the 'across' attributes of
            the ABX task. A and B share the same 'across' attributes
            and X has a different one.

        by : list, optional
            a list of strings containing the 'by' attributes of the
            ABX task. A,B and X share the same 'by' attributes.

        filters : list, optional
            a list of string specifying a filter on A, B or X.

        regressors : list, optional
            a list of string specifying a regressor on A, B or X.

        """
        self.logger = logging.getLogger('ABXpy.task')
        self.logger.debug('Creating a Task instance')

        # Load the ABX database in class attributes
        self.db_file = db_file
        self._load_database()
        self.logger.debug('{} loaded'.format(self.db_file))

        # Store input arguments as class attributes.
        # Filters and regressors are processed later.
        self.on = on
        self.across = across
        self.by = by

        # Check that those parameters are consistent with the database
        self._check_parameters_consistency()
        self.logger.debug('task parameters are consistent.')

        # If 'by' or 'across' are empty create appropriate dummy
        # columns (note that '#' is forbidden in user names for
        # columns).  Note that this additional columns are not in the
        # db_hierarchy, but I don't think this is problematic
        if not by:
            self.db['#by'] = 0
            self.by = ['#by']
        if not across:
            self.db['#across'] = range(len(self.db))
            self.across = ['#across']

        self.filters = filter_manager.FilterManager(
            self.db_hierarchy, self.on, self.across, self.by, filters)

        self.regressors = regressor_manager.RegressorManager(
            self.db, self.db_hierarchy, self.on, self.across, self.by,
            regressors)

        self.sampling = False

        # prepare the database for generating the triplets
        self.by_dbs = {}
        self.feat_dbs = {}
        self.on_blocks = {}
        self.across_blocks = {}
        self.on_across_blocks = {}
        self.antiacross_blocks = {}

        by_groups = self.db.groupby(self.by)

        display = progress_display.ProgressDisplay(self.logger)
        display.add('block', 'Preprocessing by block', len(by_groups))

        for by_key, by_frame in by_groups:
            display.update('block', 1)
            display.display()

            # allow to get by values as well as values of other
            # variables that are determined by these
            by_values = dict(by_frame.iloc[0])
            # apply 'by' filters
            if self.filters.by_filter(by_values):
                # get analogous feat_db
                by_feat_db = self.feat_db.iloc[by_frame.index]

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
                self.on_blocks[by_key] = self.by_dbs[by_key].groupby(self.on)
                self.across_blocks[by_key] = self.by_dbs[
                    by_key].groupby(self.across)
                self.on_across_blocks[by_key] = self.by_dbs[
                    by_key].groupby(self.on + self.across)
                if len(self.across) > 1:
                    self.antiacross_blocks[by_key] = dict()
                    for across_key in (self.across_blocks[by_key]
                                       .groups.iterkeys()):
                        b = True
                        for i, col in enumerate(self.across):
                            b = b * (by_frame[col] != across_key[i])
                        self.antiacross_blocks[by_key][
                            across_key] = by_frame[b].index

        # determining appropriate numeric type to represent index (currently
        # used only for numpy arrays and h5 storage, might also be used for
        # panda frames)
        types = {}
        for key, db in self.by_dbs.iteritems():
            # len(db)-1 wouldn't work here because there could be missing index
            # due to generic filtering
            n = np.max(db.index.values)
            types[key] = type_fitting.fit_integer_type(n, is_signed=False)

        self.types = types

        self.reg_block_indices = []
        # compute some statistics about the task
        self.compute_statistics()

    def _load_database(self):
        """Load a database from the provided filename.

        Load a database from self.db_file and initilizes self.db,
        self.db_hierarchy, self.feat_db.

        If the file cannot be loaded, this method raises an
        IOError exception.

        """
        # try:
        # Load the database from the items file
        self.db, self.db_hierarchy, self.feat_db = abx_database.load(
            self.db_file, features_info=True)

        # except IOError as err:
        #     # If loading raises an exception, exit the program
        #     logger.error(err)
        #     sys.exit(err)

    def _param_error(self, key, value):
        """Returns an error message"""
        return ('{} argument invalid, check that {} is defined in {}'
                .format(key, value, self.db_file))

    def _check_parameters_consistency(self):
        """Verify the consistency of the task parameters on the database.

        The following conditions are checked. The ON parameter is
        a unique string.  ON, ACROSS and BY corresponds to column
        headers in the items file. Columns names in the items file
        have no '_' or '#'.

        Moreover ACROSS and BY are transformed into lists of str, in
        case they was str.

        :raise AssertionError: if parameters are not consistent.
        """
        assert isinstance(self.on, str), 'ON attribute must be a string'

        self.on = self.on.split()  # from str to list
        assert len(self.on) == 1, 'ON attribute must specifies a unique column'

        if isinstance(self.across, str):
            self.across = [self.across]

        if isinstance(self.by, str):
            self.by = [self.by]

        # check that required columns are present
        cols = set(self.db.columns)
        # the argument of issuperset needs to be a list ...
        for p in {'ON': self.on,
                  'ACROSS': self.across,
                  'BY': self.by}.iteritems():
            assert cols.issuperset(p[1]), self._param_error(p[0], p[1])

        # TODO add additional checks, for example that columns
        # in BY, ACROSS, ON are not the same ? (see task structure notes)
        # also that location columns are not used
        for col in cols:
            assert '_' not in col, (
                col + ': you cannot use underscore in column names')
            
            assert '#' not in col, (
                col + ': you cannot use \'#\' in column names')


    def compute_statistics(self, approximate=False):
        """Compute the statistics of the task.

        The number of ABX triplets is exact in most cases if approximate is
        set to false. The other statistics can only be approxrimate in the case
        where there are A, B, X or ABX filters.

        Parameters:

        approximate : bool, optional. Approximate the number of
        triplets, default is False.
        """
        self.stats = {}

        is_approximate = bool(self.filters.A or self.filters.B or
                              self.filters.X or self.filters.ABX)
        self.stats['approximate'] = is_approximate
        self.stats['approximate_nb_triplets'] = approximate and is_approximate
        self.stats['nb_by_levels'] = len(self.by_dbs)
        self.by_stats = {}

        display = progress_display.ProgressDisplay(self.logger)
        display.add('block', 'Computing statistics for by block',
                    self.stats['nb_by_levels'])

        for by in self.by_dbs:
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
        self.stats['nb_blocks'] = sum([bystats['nb_on_across_levels']
                                       for bystats in self.by_stats.values()])

        display = progress_display.ProgressDisplay(self.logger)
        display.add(
            'block', 'Computing statistics for by/on/across block',
            self.stats['nb_blocks'])

        for by, db in self.by_dbs.iteritems():
            stats = self.by_stats[by]
            stats['block_sizes'] = {}
            stats['nb_triplets'] = 0
            stats['nb_across_pairs'] = 0
            stats['nb_on_pairs'] = 0
            # iterate over on/across blocks
            for block_key, count in stats['on_across_levels'].iteritems():
                display.update('block', 1)
                display.display()

                block = self.on_across_blocks[by].groups[block_key]
                on_across_by_values = dict(db.ix[block[0]])
                # retrieve the on and across keys (as they are stored in
                # the panda object)
                on, across = on_across_from_key(
                    block_key)
                # apply the filter and check if block is empty
                if self.filters.on_across_by_filter(on_across_by_values):
                    n_A = count
                    n_X = stats['on_levels'][on]
                    # TODO quick fix to process case whith no across, but
                    # better done in a separate loop ...
                    if self.across == ['#across']:
                        n_B = stats['nb_items'] - n_X
                    else:
                        n_B = stats['across_levels'][across] - n_A
                    n_X = n_X - n_A
                    stats['nb_across_pairs'] += n_A * n_B
                    stats['nb_on_pairs'] += n_A * n_X
                    if ((approximate or
                         not(self.filters.A or self.filters.B or
                             self.filters.X or self.filters.ABX)) and
                        type(across) != tuple):
                        stats['nb_triplets'] += n_A * n_B * n_X
                        stats['block_sizes'][block_key] = n_A * n_B * n_X
                    else:
                        # count exact number of triplets, could be further
                        # optimized because it isn't necessary to do the whole
                        # triplet generation, in particular in the case where
                        # there are no ABX filters
                        nb_triplets = self.nb_on_across_triplets(
                            by, on, across, block, on_across_by_values)
                        stats['nb_triplets'] += nb_triplets
                        stats['block_sizes'][block_key] = nb_triplets
                else:
                    stats['block_sizes'][block_key] = 0

        self.stats['nb_triplets'] = sum(
            [bystats['nb_triplets'] for bystats in self.by_stats.values()])
        # TODO remove empty by blocks then remove empty on_across_by blocks
        # here, also reset self.n_blocks in consequence
        self.n_blocks = self.stats['nb_blocks']

    def on_across_triplets(self, by, on, across, on_across_block,
                           on_across_by_values, with_regressors=True):
        """Generate all possible triplets for a given by block.

        Given an on_across_block of the database and the parameters of the \
        task, this function will generate the complete set of triplets and \
        the regressors.

        Parameters:

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

        Returns:

        triplets : numpy.Array
            the set of triplets generated
        regressors : numpy.Array
            the regressors generated
        """
        # find all possible A, B, X where A and X have the 'on' feature of the
        # block and A and B have the 'across' feature of the block
        A = np.array(on_across_block, dtype=self.types[by])
        on_set = set(self.on_blocks[by].groups[on])
        # TODO quick fix to process case whith no across, but better
        # done in a separate loop ...
        if self.across == ['#across']:
            # in this case A is a singleton and B can be anything in the by
            # block that doesn't have the same 'on' as A
            B = np.array(
                list(set(self.by_dbs[by].index).difference(on_set)),
                dtype=self.types[by])
        else:
            B = self.across_blocks[by].groups[across]
            # remove B with the same 'on' than A
            B = np.array(list(set(B).difference(A)), dtype=self.types[by])
        # remove X with the same 'across' than A

        if type(across) is tuple:
            antiacross_set = set(self.antiacross_blocks[by][across])
            X = np.array(list(antiacross_set & on_set), dtype=self.types[by])
        else:
            X = np.array(list(on_set.difference(A)), dtype=self.types[by])

        # apply singleton filters
        db = self.by_dbs[by]

        if self.filters.A:
            A = self.filters.A_filter(on_across_by_values, db, A)
        if self.filters.B:
            B = self.filters.B_filter(on_across_by_values, db, B)
        if self.filters.X:
            X = self.filters.X_filter(on_across_by_values, db, X)

        # instantiate A, B, X regressors here
        if with_regressors:
            self.regressors.set_A_regressors(on_across_by_values, db, A)
            self.regressors.set_B_regressors(on_across_by_values, db, B)
            self.regressors.set_X_regressors(on_across_by_values, db, X)

        # A, B, X can then be combined efficiently in a full (or randomly
        # sampled) factorial design
        size = len(A) * len(B) * len(X)
        on_across_block_index = [0]

        if size > 0:
            ind_type = type_fitting.fit_integer_type(size, is_signed=False)
            # if sampling in the absence of triplets filters, do it here
            if self.sampling and not(self.filters.ABX):
                indices = self.sampler.sample(size, dtype=ind_type)
            else:
                indices = np.arange(size, dtype=ind_type)
            # generate triplets from indices
            iX = np.mod(indices, len(X))
            iB = np.mod(np.divide(indices, len(X)), len(B))
            iA = np.divide(indices, len(B) * len(X))
            triplets = np.column_stack((A[iA], B[iB], X[iX]))

            # apply triplets filters
            if self.filters.ABX:
                triplets = self.filters.ABX_filter(
                    on_across_by_values, db, triplets)
                size = triplets.shape[0]
                # if sampling in the presence of triplets filters, do it here
                if self.sampling:
                    ind_type = type_fitting.fit_integer_type(
                        size, is_signed=False)
                    indices = self.sampler.sample(size, dtype=ind_type)
                    triplets = triplets[indices, :]

            if with_regressors:
                on_across_block_index = [0]
                # reindexing by regressors
                Breg = [reg[iB] for regs in self.regressors.B_regressors for reg in regs]
                Xreg = [reg[iX] for regs in self.regressors.X_regressors for reg in regs]
                regs = np.array(Breg + Xreg).T

                if len(regs) != 0:
                    n_regs = np.max(regs, 0) + 1
                    new_index = regs[:, 0].astype(ind_type)
                    for i in range(1, len(n_regs)):
                        new_index = regs[:, i] + n_regs[i] * new_index

                    permut = np.argsort(new_index)
                    # TODO replace with empty array and fill it
                    new_permut = sort_and_threshold(
                        permut, new_index, ind_type, on_across_block_index,
                        threshold=self.threshold)

                    # TODO add other regs, replace reg_block by indexes for collapse
                    iA = iA[new_permut]
                    iB = iB[new_permut]
                    iX = iX[new_permut]
                    triplets = triplets[new_permut]


        else:
            # empty block...
            triplets = np.empty(shape=(0, 3), dtype=self.types[by])
            indices = np.empty(shape=size, dtype=np.uint8)
            iA = indices
            iB = indices
            iX = indices

        if with_regressors:
            if self.regressors.ABX:  # instantiate ABX regressors here
                self.regressors.set_ABX_regressors(
                    on_across_by_values, db, triplets)

            # self.regressors.XXX contains either (for by and on_across_by)
            #   [[scalar_output_1_dbfun_1, scalar_output_2_dbfun_1,...],
            #    [scalar_output_1_dbfun_2, ...], ...]
            # or:
            #   [[np_array_output_1_dbfun_1, np_array_output_2_dbfun_1,...],
            #    [np_array_output_1_dbfun_2, ...], ...]
            # TODO change manager API so that self.regressors.A contains the
            # data and not the list of dbfun_s ?
            regressors = {}
            scalar_names = self.regressors.by_names + \
                self.regressors.on_across_by_names
            scalar_regressors = self.regressors.by_regressors + \
                self.regressors.on_across_by_regressors
            for names, regs in zip(scalar_names, scalar_regressors):
                for name, reg in zip(names, regs):
                    regressors[name] = np.tile(np.array(reg),
                                               (np.size(triplets, 0), 1))
            for names, regs in zip(self.regressors.A_names,
                                   self.regressors.A_regressors):
                for name, reg in zip(names, regs):
                    regressors[name] = reg[iA]
            for names, regs in zip(self.regressors.B_names,
                                   self.regressors.B_regressors):
                for name, reg in zip(names, regs):
                    regressors[name] = reg[iB]
            for names, regs in zip(self.regressors.X_names,
                                   self.regressors.X_regressors):
                for name, reg in zip(names, regs):
                    regressors[name] = reg[iX]
            # TODO implement this
            # for names, regs in zip(self.regressors.ABX_names,
            #                        self.regressors.ABX_regressors):
            #    for name, reg in zip(names, regs):
            #        regressors[name] = reg[indices,:]
            return (triplets, regressors,
                    np.reshape(np.array(on_across_block_index),
                               (len(on_across_block_index), 1)))
        else:
            return triplets


    def nb_on_across_triplets(self, by, on, across, on_across_block,
                              on_across_by_values):
        """Count all possible triplets for a given by block. Does not take in
        account sample or threshold.

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
        nb_triplets : int
            the number of triplets to generate
        """
        # find all possible A, B, X where A and X have the 'on' feature of the
        # block and A and B have the 'across' feature of the block
        A = np.array(on_across_block, dtype=self.types[by])
        on_set = set(self.on_blocks[by].groups[on])
        # TODO quick fix to process case whith no across, but better done in a
        # separate loop ...
        if self.across == ['#across']:
            # in this case A is a singleton and B can be anything in the by
            # block that doesn't have the same 'on' as A
            B = np.array(
                list(set(self.by_dbs[by].index).difference(on_set)),
                dtype=self.types[by])
        else:
            B = self.across_blocks[by].groups[across]
            # remove B with the same 'on' than A
            B = np.array(list(set(B).difference(A)), dtype=self.types[by])
        # remove X with the same 'across' than A

        if type(across) is tuple:
            antiacross_set = set(self.antiacross_blocks[by][across])
            X = np.array(list(antiacross_set & on_set), dtype=self.types[by])
        else:
            X = np.array(list(on_set.difference(A)), dtype=self.types[by])

        # apply singleton filters
        db = self.by_dbs[by]

        if self.filters.A:
            A = self.filters.A_filter(on_across_by_values, db, A)
        if self.filters.B:
            B = self.filters.B_filter(on_across_by_values, db, B)
        if self.filters.X:
            X = self.filters.X_filter(on_across_by_values, db, X)

        # A, B, X can then be combined efficiently in a full (or randomly
        # sampled) factorial design
        size = len(A) * len(B) * len(X)

        if size > 0:
            ind_type = type_fitting.fit_integer_type(size, is_signed=False)
            indices = np.arange(size, dtype=ind_type)
            # generate triplets from indices
            iX = np.mod(indices, len(X))
            iB = np.mod(np.divide(indices, len(X)), len(B))
            iA = np.divide(indices, len(B) * len(X))
            triplets = np.column_stack((A[iA], B[iB], X[iX]))

            # apply triplets filters
            if self.filters.ABX:
                triplets = self.filters.ABX_filter(
                    on_across_by_values, db, triplets)

        else:
            # empty block...
            triplets = np.empty(shape=(0, 3), dtype=self.types[by])

        return triplets.shape[0]

    # TODO in case of sampling, get rid of blocks with no samples ?
    def generate_triplets(self, output=None, sample=None, threshold=None):
        """Generate all possible triplets for the whole task and the
        associated pairs

        Generate the triplets and the pairs for an ABXpy.Task and store it in
        a h5db file.

        Parameters:

        output : filename, optional. The output file. If not
                 specified, it will automatically create a new file
                 with the same name as the input file.

        sample : bool, optional. Apply the function on a sample of
                 the task

        """
        if self.stats['nb_triplets'] == 0:
            warnings.warn('There are no possible ABX triplets'
                          ' in the specified task', UserWarning)
            return

        # TODO change this to a random file name to avoid
        # overwriting problems default name for output file
        if output is None:
            (basename, _) = os.path.splitext(self.db_file)
            output = basename + '.abx'

        # TODO use an object that guarantees that the stream will not be
        # perturbed by external codes calls to np.random
        # set up sampling if any
        self.total_n_triplets = self.stats['nb_triplets']
        if sample is not None:
            self.sampling = True
            if self.stats['approximate_nb_triplets']:
                raise ValueError('Cannot sample if number of triplets is \
                    computed approximately')
            # TODO for now just something as random a possible
            np.random.seed()
            N = self.total_n_triplets
            if sample < 1:  # proportion of triplets to be sampled
                sample = np.uint64(round(sample * N))
            self.sampler = sampler.IncrementalSampler(N, sample)
            self.n_triplets = sample
        else:
            self.sampling = False
            self.n_triplets = self.total_n_triplets

        if threshold is not None:
            self.threshold = threshold
        else:
            self.threshold = False

        # display=None
        display = progress_display.ProgressDisplay(self.logger)
        display.add(
            'block', 'Computing triplets for by/on/across block',
            self.n_blocks)
        display.add(
            'triplets', 'Triplets considered:', self.total_n_triplets)
        display.add(
            'sampled_triplets', 'Triplets sampled:', self.n_triplets)

        self.by_block_indices = [0]
        self.current_index = 0
        # fill output file with list of needed ABX triplets, it is done
        # independently for each 'by' value

        with np2h5.NP2H5(h5file=output) as fh:
            # TODO test if not fixed size impacts performance a lot
            out = fh.add_dataset(
                group='triplets', dataset='data',
                n_rows=self.n_triplets, n_columns=3,
                item_type=type_fitting.fit_integer_type(self.total_n_triplets),
                fixed_size=False)

            out_block_index = fh.add_dataset(
                group='triplets', dataset='on_across_block_index',
                n_rows=self.stats['nb_blocks'], n_columns=1,
                item_type=type_fitting.fit_integer_type(self.stats['nb_blocks']),
                fixed_size=False)  #TODO add item type
            to_delete = []
            bys = []
            for by, db in self.by_dbs.iteritems():
                # class for efficiently writing to datasets of the output file
                # (using a buffer under the hood)
                self.logger.info("Writing ABX triplets to task file...")

                # allow to get by values as well as values of other
                # variables that are determined by these
                by_values = dict(db.iloc[0])

                datasets, indexes = self.regressors.get_regressor_info()
                with (h5io.H5IO(
                        filename=output, datasets=datasets,
                        indexes=indexes,
                        group='/regressors/' + str(by) + '/')) as out_regs:
                    self._compute_triplets(
                        by, out, out_block_index,
                        out_regs, sample, db, fh, by_values, display=display)

                    # if no triplets found: delete by block
                    if self.current_index == self.by_block_indices[-1]:
                        to_delete.append(by)
                    else:
                        self.by_block_indices.append(self.current_index)
                        bys.append(by)

            aux = np.array(self.by_block_indices)
            out_by_index = fh.add_dataset(
                group='triplets', dataset='by_index',
                n_rows=len(aux)-1, n_columns=2,
                item_type=type_fitting.fit_integer_type(aux[-1]),
                fixed_size=True)
            self.by_block_indices = np.hstack((aux[:-1, None], aux[1:, None]))
            out_by_index.write(self.by_block_indices)
            for by in to_delete:
                del self.by_dbs[by]
            fh.file.create_dataset(
                'bys', (aux.shape[0] -1,),
                dtype=h5py.special_dtype(vlen=unicode))
            fh.file['bys'][:] = [str(by) for by in bys]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", NaturalNameWarning)
            self.generate_pairs(output)

    def _compute_triplets(self, by, out, out_block_index,
                          out_regs, sample, db, fh, by_values, display=None):
        #out_index = h5io.H5IO(filename=output, datasets=datasets,
        #group='/on_across_block_index/' + str(by) + '/')

        # instantiate by regressors here
        self.regressors.set_by_regressors(by_values)

        # iterate over on/across blocks
        for block_key, block in (self.on_across_blocks[by]
                                 .groups.iteritems()):
            if display is not None:
                display.update('block', 1)
            # allow to get on, across, by values as well as values
            # of other variables that are determined by these
            on_across_by_values = dict(db.ix[block[0]])
            if ((self.filters
                 .on_across_by_filter(on_across_by_values))):
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
                if display is not None:
                    display.update(
                        'sampled_triplets', triplets.shape[0])
                    display.update('triplets',
                                   (self.by_stats[by]
                                    ['block_sizes'][block_key]))
            if display is not None:
                display.display()

    # TODO clean this function (maybe do a few well-separated
    # sub-functions for getting the pairs and unique them)
    def generate_pairs(self, output=None):
        """Generate the pairs associated to the triplet list

        .. note:: This function is called by generate_triplets and
            should not be used independantly

        """
        # TODO change this to a random file name to avoid
        # overwriting problems default name for output file
        if output is None:
            (basename, _) = os.path.splitext(self.db_file)
            output = basename + '.abx'
        # list all pairs
        n_pairs_dict = {}
        max_ind_dict = {}
        try:
            _, output_tmp = tempfile.mkstemp()
            for n_by, (by, db) in enumerate(self.by_dbs.iteritems()):
                self.logger.info("Writing AX/BX pairs to task file...")
                with h5py.File(output) as fh:
                    triplets_attrs = fh['/triplets']['by_index'][n_by][...]
                if triplets_attrs[0] == triplets_attrs[1]:
                    # subdataset is empty
                    continue
                max_ind = np.max(db.index.values)
                max_ind_dict[by] = max_ind
                pair_key_type = type_fitting.fit_integer_type(
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
                            # would need to amend np2h5 and h52np to remove
                            # the second dim...
                            pairs = np.empty(
                                shape=(2 * n, 1), dtype=pair_key_type)
                            # TODO change the encoding (and type_fitting)
                            # so that A,B and B,A have the same code ...
                            # (take a=min(a,b), b=max(a,b))
                            # TODO but allow a flag to control the
                            # behavior to be able to enforce A,X and B,X
                            # order when using assymetrical distance
                            # functions
                            pairs[i1, 0] = triplets[:, 0] + (
                                max_ind + 1) * triplets[:, 2]  # AX
                            pairs[i2, 0] = triplets[:, 1] + (
                                max_ind + 1) * triplets[:, 2]  # BX
                            # TODO do a unique here already? Do not store
                            # the inverse mapping ? (could sort triplets on
                            # pair1, complete pair1, sort on pair2,
                            # complete pair 2 and shuffle ?)
                            out.write(pairs)

                    # sort pairs
                    handler = h5_handler.H5Handler(output_tmp,
                                                   '/pairs/',
                                                   str(by))

                    # memory: available RAM in Mo, could be a param
                    memory = 1000
                    # estimate of the amount of data to be sorted
                    with h5py.File(output_tmp) as fh:
                        n = fh['/pairs/' + str(by)].shape[0]
                        i = fh['/pairs/' + str(by)].dtype.itemsize
                    amount = n * i  # in bytes
                    # harmonize units to Ko:
                    memory = 1000 * memory
                    amount = amount / 1000.
                    # be conservative: aim at using no more than 3/4
                    # the available memory if enough memory take one
                    # chunk (this will do an unnecessary full write
                    # and read of the file... could be optimized
                    # easily)
                    if amount <= 0.75 * memory:
                        # would it be beneficial to have a large
                        # o_buffer_size as well ?
                        handler.sort(buffer_size=amount)
                    # else take around 30 chunks if possible (this
                    # seems efficient given the current implem, using
                    # a larger number of chunks efficiently might be
                    # possible if the reading chunks part of the sort
                    # was cythonized ?)
                    elif amount / 30. <= 0.75 * memory:
                        handler.sort(buffer_size=amount / 30.)
                    # else take minimum number of chunks possible given the
                    # available RAM
                    else:
                        handler.sort(buffer_size=0.75 * memory)

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

                    # TODO should have a unique function directly instead of
                    # sorting + unique ?
                    with np2h5.NP2H5(output_tmp) as f_out:
                        with h52np.H52NP(output_tmp) as f_in:
                            inp = f_in.add_dataset('pairs', str(by))
                            out = f_out.add_dataset(
                                'unique_pairs', str(by), n_rows=n_pairs, n_columns=1,
                                item_type=pair_key_type, fixed_size=False)
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
                        # use append to make use of table format, which is better at
                        # handling strings without much space (fixed-size format)
                        store.append('/feat_dbs/' + str(by), self.feat_dbs[by],
                                     expectedrows=len(self.feat_dbs[by]))
                        store.close()
                        # TODO generate inverse mapping to triplets (1 and 2) ?

            # Now merge all datasets
            by_index = 0
            with np2h5.NP2H5(output) as f_out:
                n_rows = sum(n_pairs_dict.itervalues())
                out_unique_pairs = f_out.add_dataset(
                    'unique_pairs', 'data', n_rows=n_rows, n_columns=1,
                    item_type=np.int64, fixed_size=False)
                for n_by, (by, db) in enumerate(self.by_dbs.iteritems()):
                    triplets_attrs = f_out.file['/triplets']['by_index'][n_by]
                    if triplets_attrs[0] == triplets_attrs[1]:
                        # subdataset is empty
                        continue

                    with h52np.H52NP(output_tmp) as f_in:
                        inp = f_in.add_dataset('unique_pairs', str(by))
                        for pairs in inp:
                            out_unique_pairs.write(pairs)

                    with h5py.File(output) as fh:
                        fh['/unique_pairs'].attrs[str(by)] = (
                            max_ind_dict[by] + 1, by_index, by_index + n_pairs_dict[by])
                    by_index += n_pairs_dict[by]
        finally:
            os.remove(output_tmp)

    # number of triplets when triplets with same on, across, by are counted as
    # one
    # TODO current implementation won't work with A, B, X or ABX filters
    # TODO lots of code in this function is repicated from
    # on_across_triplets, generate_triplets and/or compute_stats: the maximum
    # possible should be factored out, including the loop over by, loop over
    # on_across iteration structure
    def compute_nb_levels(self):
        if self.filters.A or self.filters.B or self.filters.X or \
           self.filters.ABX:
            raise ValueError(
                'Current implementation do not support computing nb_levels in '
                'the presence of A, B, X, or ABX filters')

        display = progress_display.ProgressDisplay(self.logger)
        display.add(
            'block', 'Computing nb_levels for by block',
            self.stats['nb_by_levels'])

        for by, db in self.by_dbs.iteritems():
            display.update('block', 1)
            display.display()

            n = 0
            # iterate over on/across blocks
            for block_key, n_block in (self.by_stats[by]['on_across_levels']
                                       .iteritems()):
                block = self.on_across_blocks[by].groups[block_key]
                on_across_by_values = dict(db.ix[block[0]])
                on, across = on_across_from_key(block_key)
                if self.filters.on_across_by_filter(on_across_by_values):
                    # find all possible A, B, X where A and X have the 'on'
                    # feature of the block and A and B have the 'across'
                    # feature of the block
                    on_across_block = self.on_across_blocks[
                        by].groups[block_key]
                    A = np.array(on_across_block, dtype=self.types[by])
                    X = self.on_blocks[by].groups[on]
                    # TODO quick fix to process case whith no across, but
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
        self.stats['nb_levels'] = sum([stats['nb_levels']
                                       for stats in self.by_stats.values()])

    def print_stats(self, filename=None, summarized=True):
        """Print basic statistics on the task to a file.

        This is a simple wrapper to Task.print_stats_to_stream().

        Parameters:

        filename: str, optional. The file where to write
            statistics. If not provided, write on stdout.

        summarized: bool, optional. Write shorter statistics if True
            (default), complete stats if False.
        """
        if not filename:
            self.print_stats_to_stream(sys.stdout, summarized)
        else:
            with open(filename, 'w') as f:
                self.print_stats_to_stream(f, summarized)

    def print_stats_to_stream(self, stream=sys.stdout, summarized=True):
        """Print basic statistics on the task to a stream.

        TODO comment...
        """
        stream.write('\n\n###### Global stats ######\n\n')
        pprint.pprint(self.stats, stream)
        stream.write('\n\n###### by blocks stats ######\n\n')
        if summarized:
            for by, stats in self.by_stats.iteritems():
                stream.write('### by level: %s ###\n' % str(by))
                pprint.pprint(stats, stream)
        else:
            try:
                self.compute_nb_levels()
            except ValueError:
                self.logger.warning('Filters not fully supported, '
                                    'nb_levels per by block wont be calculated')
            for by, stats in self.by_stats.iteritems():
                stream.write('### by level: %s ###\n' % str(by))
                stream.write('nb_triplets: %d\n' % stats['nb_triplets'])
                if 'nb_levels' in stats:
                    stream.write('nb_levels: %d\n' % stats['nb_levels'])
                stream.write('nb_across_pairs: %d\n' %
                             stats['nb_across_pairs'])
                stream.write('nb_on_pairs: %d\n' % stats['nb_on_pairs'])
                stream.write('nb_on_levels: %d\n' % stats['nb_on_levels'])
                stream.write('nb_across_levels: %d\n' %
                             stats['nb_across_levels'])
                stream.write('nb_on_across_levels: %d\n' %
                             stats['nb_on_across_levels'])


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


#@nb.autojit
def sort_and_threshold(permut, new_index, ind_type,
                       on_across_block_index, threshold=None):
    new_permut = []
    i_unique = 0
    key_reg = new_index[permut[0]]
    reg_block = np.empty((len(permut), 2), dtype=np.int64)
    i_start = 0
    i = 0
    for i, p in enumerate(permut[1:]):
        i += 1
        if new_index[p] != key_reg:
            reg_block[i_unique] = [i_start, i]
            count = i - i_start
            if threshold and count > threshold:
                # sampling this 'on across by' block
                sampled_block_indexes = (
                    i_start + \
                    sampler.sample_without_replacement(
                        threshold, count, dtype=ind_type))
                new_permut.extend(permut[sampled_block_indexes])
                on_across_block_index.append(
                    on_across_block_index[-1] + threshold)
            else:
                new_permut.extend(permut[i_start:i])
                on_across_block_index.append(
                    on_across_block_index[-1] + count)
            i_start = i
            i_unique += 1
            key_reg = new_index[p]

    reg_block[i_unique] = [i_start, i + 1]
    reg_block = np.resize(reg_block, (i_unique + 1, 2))
    count = i + 1 - i_start
    if threshold and count > threshold:
        # sampling this 'on across by' block
        sampled_block_indexes = (
            i_start + sampler.sample_without_replacement(
                threshold, count, dtype=ind_type))
        new_permut.extend(permut[sampled_block_indexes])
    else:
        new_permut.extend(permut[i_start:i+1])
    return new_permut
