# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 16:59:27 2013

@author: Thomas Schatz
"""  


""" Abstract API for getting functions of data in a database """
# API define one attribute (input_names) and one method (evaluate)
class DBfun(object):
    
    def __init__(self, input_names):
        self.input_names = input_names
    
    # input must contain a dictionary whos keys are the input_names
    def evaluate(self, inputs_dict):
        pass
        # do some generic checks here ? 
        # e.g. set(input_names) == set(input_dict.keys())
        # or each element in inputs_dict is an array with the same number of lines (and possibly different types and number of columns)

    # should return at least the number of outputs and if possible an ordered list of output names + a dictionary {output_name: index} containing all indexed outputs and their indexes
    def output_specs(self):
        pass# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 16:59:27 2013

@author: Thomas Schatz
"""


""" Abstract API for getting functions of data in a database """
# API define one attribute (input_names) and one method (evaluate)


class DBfun(object):

    def __init__(self, input_names):
        self.input_names = input_names

    # input must contain a dictionary whos keys are the input_names
    def evaluate(self, inputs_dict):
        pass
        # do some generic checks here ?
        # e.g. set(input_names) == set(input_dict.keys())
        # or each element in inputs_dict is an array with the same number of
        # lines (and possibly different types and number of columns)

    # should return at least the number of outputs and if possible an ordered
    # list of output names + a dictionary {output_name: index} containing all
    # indexed outputs and their indexes
    def output_specs(self):
        pass
