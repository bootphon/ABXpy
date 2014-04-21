# -*- coding: utf-8 -*-
"""
Created on Mon Dec 16 05:01:53 2013

@author: Thomas Schatz
"""

# make sure the rest of the ABXpy package is accessible
import os, sys
package_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
if not(package_path in sys.path):
    sys.path.append(package_path)

import ABXpy.sideop.side_operations_manager as side_operations_manager
import ABXpy.dbfun.dbfun_compute as dbfun_compute
import ABXpy.dbfun.dbfun_lookuptable as dbfun_lookuptable
import ABXpy.dbfun.dbfun_column as dbfun_column


class RegressorManager(side_operations_manager.SideOperationsManager):
    
    def __init__(self, db, db_hierarchy, on, across, by, regressors):
        side_operations_manager.SideOperationsManager.__init__(self, db_hierarchy, on, across, by)  
        # add column functions for the default regressors: on_AB, on_X, across_AX(s), across_B(s) (but not the by(s))      
        default_regressors = [on[0] + '_1', on[0] + '_2']
        for col in self.across_cols:
            default_regressors.append(col+'_1')
            default_regressors.append(col+'_2')
        #FIXME add default regressors only if they are not already specified ?
        regressors = regressors + default_regressors
        
        for reg in regressors: # reg can be: the name of a column of the database (possibly extended), the name of lookup file, the name of a script, a script under the form of a string (that doesnt end by .dbfun...)
             # instantiate appropriate dbfun
            if reg in self.extended_cols: # column already in db
                col, _ = self.parse_extended_column(reg)
                db_fun = dbfun_column.DBfun_Column(reg, db, col, indexed=True)                               
            elif len(reg) >= 6 and reg[-6:] == '.dbfun': # lookup table
                db_fun = dbfun_lookuptable.DBfun_LookupTable(reg, indexed=True) # ask for re-interpreted indexed outputs
            else: # on the fly computation
                db_fun = dbfun_compute.DBfun_Compute(reg, self.extended_cols)             
            self.add(db_fun)
            
        # regressor names and regressor index if needed
        
    
    # for generics: generate three versions of the regressor: _A, _B, and _X 
    def classify_generic(self, elements, db_fun, db_variables):
        # check if there are only non-extended names 
        if {s for r, s in elements} == set(['']):
            # for now raise an exception 
            raise ValueError('You need to explicitly specify the columns for which you want regressors (using _A, _B and _X extensions)')
            #FIXME finish the following code to replace the current exception ...
            # change the code and/or the synopsis to replace all columns by their name +'_A', '_B', or '_X' 
            #if db_fun.mode == 'table lookup':
            #    definition = "with '%s' as reg: reg(%s%s, %s%s, ...)" % (db_fun.h5_file, db_fun.in_names[0], ext, db_fun.in_names[1], ext, ...)                
            #else:
            #    definition = f(db_fun.script) # f replaces all occurences of db_fun.extended_variables in the script string by _A,... version 
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
        
               
    def set_by_regressors(self, by_values): self.by_regressors = [result for result in self.evaluate_by(by_values)]      
      
    def set_on_across_by_regressors(self, on_across_by_values): self.on_across_by_regressors = [result for result in self.evaluate_on_across_by(on_across_by_values)]     
        
    def set_A_regressors(self, on_across_by_values, db, indices): self.A_regressors = [result for result in self.evaluate_A(on_across_by_values, db, indices)]
    def set_B_regressors(self, on_across_by_values, db, indices): self.B_regressors = [result for result in self.evaluate_B(on_across_by_values, db, indices)]
    def set_X_regressors(self, on_across_by_values, db, indices): self.X_regressors = [result for result in self.evaluate_X(on_across_by_values, db, indices)]

    #FIXME implement ABX regressors
    def set_ABX_regressors(self, on_across_by_values, db, triplets): raise ValueError('ABX regressors not implemented')
        
    #FIXME current implem (here and also in dbfun.get_indexes), does not allow index sharing...
    #FIXME can there be name conflicts with this implem ?
    def get_regressor_info(self): # implem a bit redundant
        names = []
        indexes = {}
        self.fetch_regressor_info('by')
        self.fetch_regressor_info('on_across_by')
        self.fetch_regressor_info('A')
        self.fetch_regressor_info('B')
        self.fetch_regressor_info('X')     
        self.fetch_regressor_info('ABX')
        for db_fun in self.by + self.on_across_by + self.A + self.B + self.X + self.ABX:
            o_names, o_indexes = db_fun.get_indexes()
            names = names+o_names
            for key, index in o_indexes.iteritems():
                indexes[key] = index
        return names, indexes
        
        
    def fetch_regressor_info(self, field):
        setattr(self, field+'_names', [])
        setattr(self, field+'_indexes', [])
        for db_fun in getattr(self, field):
            o_names, o_indexes = db_fun.get_indexes()
            getattr(self, field+'_names').append(o_names)
            getattr(self, field+'_indexes').append(o_indexes)