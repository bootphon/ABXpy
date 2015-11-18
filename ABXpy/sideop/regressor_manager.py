# -*- coding: utf-8 -*-
"""
Created on Mon Dec 16 05:01:53 2013

:author: Thomas Schatz
"""

# make sure the rest of the ABXpy package is accessible
import os
import sys

import ABXpy.sideop.side_operations_manager as side_operations_manager
import ABXpy.dbfun.dbfun_compute as dbfun_compute
import ABXpy.dbfun.dbfun_lookuptable as dbfun_lookuptable
import ABXpy.dbfun.dbfun_column as dbfun_column


class RegressorManager(side_operations_manager.SideOperationsManager):

    """Manage the regressors on attributes (on, across, by) or elements (A, B,
    X) for further processing
    """

    def __init__(self, db, db_hierarchy, on, across, by, regressors):
        side_operations_manager.SideOperationsManager.__init__(
            self, db_hierarchy, on, across, by)
        # add column functions for the default regressors: on_AB, on_X,
        # across_AX(s), across_B(s) (but not the by(s))
        default_regressors = [on[0] + '_1', on[0] + '_2']
        # check if no across were specified
        if not(self.across_cols == set(["#across"])):
            for col in self.across_cols:
                default_regressors.append(col + '_1')
                default_regressors.append(col + '_2')
        # FIXME: add default regressors only if they are not already specified ?
        # FIXME: do we really need to add the columns deriving from the original
        # on and across?
        regressors = regressors + default_regressors

        # reg can be: the name of a column of the database (possibly extended),
        # the name of lookup file, the name of a script, a script under the
        # form of a string (that doesnt end by .dbfun...)
        for reg in regressors:
            # instantiate appropriate dbfun
            if reg in self.extended_cols:  # column already in db
                col, _ = self.parse_extended_column(reg)
                db_fun = dbfun_column.DBfun_Column(reg, db, col, indexed=True)
            elif len(reg) >= 6 and reg[-6:] == '.dbfun':  # lookup table
                # ask for re-interpreted indexed outputs
                db_fun = dbfun_lookuptable.DBfun_LookupTable(reg, indexed=True)
            else:  # on the fly computation
                db_fun = dbfun_compute.DBfun_Compute(reg, self.extended_cols)
            self.add(db_fun)

        # regressor names and regressor index if needed

    # for generics: generate three versions of the regressor: _A, _B, and _X
    def classify_generic(self, elements, db_fun, db_variables):
        # check if there are only non-extended names
        if {s for r, s in elements} == set(['']):
            # for now raise an exception
            raise ValueError(
                'You need to explicitly specify the columns for which you want regressors (using _A, _B and _X extensions)')
            # FIXME: finish the following code to replace the current exception ...
            # change the code and/or the synopsis to replace all columns by their name +'_A', '_B', or '_X'
            # if db_fun.mode == 'table lookup':
            #    definition = "with '%s' as reg: reg(%s%s, %s%s, ...)" % (db_fun.h5_file, db_fun.in_names[0], ext, db_fun.in_names[1], ext, ...)
            # else:
            # definition = f(db_fun.script) # f replaces all occurences of db_fun.extended_variables in the script string by _A,... version
            # need a function to regenerate python code from the a modified ast for this.
            # is it always a DBfun_Compute ?
            #            reg_A = dbfun_compute.DBfun_Compute(definition, self.extended_columns)
            #            reg_B = dbfun_compute.DBfun_Compute(definition, self.extended_columns)
            #            reg_X = dbfun_compute.DBfun_Compute(definition, self.extended_columns)
            #            self.add(reg_A)
            #            self.add(reg_B)
            #            self.add(reg_X)
            #elements = {}
        return elements, db_variables

    def set_by_regressors(self, by_values):
        self.by_regressors = [result for result in self.evaluate_by(by_values)]

    def set_on_across_by_regressors(self, on_across_by_values):
        self.on_across_by_regressors = [
            result for result in self.evaluate_on_across_by(on_across_by_values)]

    def set_A_regressors(self, on_across_by_values, db, indices):
        self.A_regressors = [
            result for result in self.evaluate_A(on_across_by_values, db, indices)]

    def set_B_regressors(self, on_across_by_values, db, indices):
        self.B_regressors = [
            result for result in self.evaluate_B(on_across_by_values, db, indices)]

    def set_X_regressors(self, on_across_by_values, db, indices):
        self.X_regressors = [
            result for result in self.evaluate_X(on_across_by_values, db, indices)]

    # FIXME: implement ABX regressors
    def set_ABX_regressors(self, on_across_by_values, db, triplets):
        raise ValueError('ABX regressors not implemented')

    # FIXME: current implem (here and also in dbfun.output_specs), does not
    # allow index sharing...
    def get_regressor_info(self):
        names = []
        indexes = {}
        reg_id = 0
        reg_id = self.fetch_regressor_info('by', reg_id)
        reg_id = self.fetch_regressor_info('on_across_by', reg_id)
        reg_id = self.fetch_regressor_info('A', reg_id)
        reg_id = self.fetch_regressor_info('B', reg_id)
        reg_id = self.fetch_regressor_info('X', reg_id)
        reg_id = self.fetch_regressor_info('ABX', reg_id)
        for field in ['by', 'on_across_by', 'A', 'B', 'X', 'ABX']:
            names = names + \
                [name for name_list in getattr(
                    self, field + '_names') for name in name_list]
            for dictionary in getattr(self, field + '_indexes'):
                for key, index in dictionary.iteritems():
                    indexes[key] = index
        return names, indexes

    def fetch_regressor_info(self, field, reg_id):
        setattr(self, field + '_names', [])
        setattr(self, field + '_indexes', [])
        for db_fun in getattr(self, field):
            nb_o, o_names, o_indexes = db_fun.output_specs()
            if o_names is None:  # give arbitrary names
                o_names = ['reg_' + str(reg_id + n) for n in range(nb_o)]
                reg_id = reg_id + nb_o
            getattr(self, field + '_names').append(o_names)
            getattr(self, field + '_indexes').append(o_indexes)
        return reg_id
