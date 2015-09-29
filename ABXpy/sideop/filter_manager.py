# -*- coding: utf-8 -*-
"""
Created on Mon Dec 16 05:00:10 2013

@author: Thomas Schatz
"""

import numpy as np
import os
import sys

import ABXpy.sideop.side_operations_manager as side_operations_manager
import ABXpy.dbfun.dbfun_compute as dbfun_compute
import ABXpy.dbfun.dbfun_lookuptable as dbfun_lookuptable
import ABXpy.dbfun.dbfun_column as dbfun_column


class FilterManager(side_operations_manager.SideOperationsManager):

    """Manage the filters on attributes (on, across, by) or elements (A, B, X)
    for further processing"""

    def __init__(self, db_hierarchy, on, across, by, filters):
        side_operations_manager.SideOperationsManager.__init__(
            self, db_hierarchy, on, across, by)
        # this case is specific to filters, it applies a generic filter to the
        # database before considering A, B and X stuff.
        self.generic = []

        # associate each of the provided filters to the appropriate point in
        # the computation flow
        # filt can be: the name of a column of the database (possibly
        # extended), the name of lookup file, the name of a script, a script
        # under the form of a string (that doesnt end by .dbfun...)
        for filt in filters:
             # instantiate appropriate dbfun
            if filt in self.extended_cols:  # column already in db
                db_fun = dbfun_column.DBfun_Column(filt, indexed=False)
                # evaluate context is wasteful in this case... not even
                # necessary to have a dbfun at all
            elif len(filt) >= 6 and filt[-6:] == '.dbfun':  # lookup table
                # ask for re-interpreted indexed outputs
                db_fun = dbfun_lookuptable.DBfun_LookupTable(
                    filt, indexed=False)
            else:  # on the fly computation
                db_fun = dbfun_compute.DBfun_Compute(filt, self.extended_cols)
            self.add(db_fun)

    def classify_generic(self, elements, db_fun, db_variables):
        # check if there are only non-extended names and, only if this is the
        # case, instantiate 'generic' field of db_variables
        if {s for r, s in elements} == set(['']):
            db_variables['generic'] = set(elements)
            self.generic.append(db_fun)
            self.generic_context['generic'].update(db_variables['generic'])
            elements = {}
        return elements, db_variables

    def by_filter(self, by_values):
        return singleton_filter(self.evaluate_by(by_values))

    def generic_filter(self, by_values, db):
        return db.iloc[vectorial_filter(lambda context: self.evaluate_generic(by_values, db, context), np.arange(len(db)))]

    def on_across_by_filter(self, on_across_by_values):
        return singleton_filter(self.evaluate_on_across_by(on_across_by_values))

    def A_filter(self, on_across_by_values, db, indices):
        return vectorial_filter(lambda context: self.evaluate_A(on_across_by_values, db, indices, context), indices)

    def B_filter(self, on_across_by_values, db, indices):
        return vectorial_filter(lambda context: self.evaluate_B(on_across_by_values, db, indices, context), indices)

    def X_filter(self, on_across_by_values, db, indices):
        return vectorial_filter(lambda context: self.evaluate_X(on_across_by_values, db, indices, context), indices)

    # FIXME:implement ABX_filter
    def ABX_filter(self, on_across_by_values, db, triplets):
        raise ValueError('ABX filters not implemented')


def singleton_filter(generator):
    keep = True
    for result in generator:
        if not(result):
            keep = False
            break
    return keep


def vectorial_filter(generator, indices):
    """

    .. note:: To allow a lazy evaluation of the filter, the context is filtered
        explicitly which acts on the generator by a side-effect (dict being
        mutable in python)

    """
    kept = indices
    context = {}
    for result in generator(context):
        still_up = np.where(result)[0]
        kept = kept[still_up]
        for var in context:
            # keep testing only the case that are still possibly True
            context[var] = [context[var][e] for e in still_up]
            # FIXME wouldn't using only numpy arrays be more performant ?
        if not(kept.size):
            break
    return kept
