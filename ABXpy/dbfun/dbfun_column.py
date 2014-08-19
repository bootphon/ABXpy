# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20 13:36:52 2013

@author: Thomas Schatz
"""

import numpy as np
import dbfun


class DBfun_Column(dbfun.DBfun):

    def __init__(self, name, db=None, column=None, indexed=True):
        self.input_names = [name]
        self.n_outputs = 1
        if indexed:
            index = list(set(db[column]))
            index.sort()
            self.index = index
        else:
            self.index = []

    def output_specs(self):
        if self.index:
            indexes = {self.input_names[0]: self.index}
        else:
            indexes = {}
        return self.n_outputs, self.input_names, indexes

    # function for evaluating the column function given data for the context
    # context is a dictionary with just the right name/content associations
    def evaluate(self, context):
        if self.index:
            # FIXME optimize this
            return [np.array([self.index.index(e)
                    for e in context[self.input_names[0]]])]
        else:
            return [context[self.input_names[0]]]
