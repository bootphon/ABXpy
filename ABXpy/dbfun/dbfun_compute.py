# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 16:59:27 2013

@author: Thomas Schatz

Class for defining and computing efficiently functions of the columns of a database.
Implements the DBfun API  
""" 

 
import ast
import dbfun, dbfun_lookuptable, lookuptable_connector


#FIXME remove dbfun prefix from dbfun_lookuptable and dbfun_connector ?
class DBfun_Compute(dbfun.DBfun):
    
    def __init__(self, definition, columns):
            
        self.columns = set(columns)
        # set script 
        if len(definition) >= 3 and definition[-3:] == '.py':
            with open(definition) as script_file:                    
                self.script = script_file.read()
        else:
            self.script = definition
        self.parse()

    
    # slow but not likely to be critical       
    def parse(self):        
        """
        first separate the script defining the function into various components (import statements, with 'h5file' statement, synopsis definition, main code)
        """
        tree = ast.parse(self.script)        
        # find and extract imports
        imports = [stat for stat in tree.body if isinstance(stat, (ast.ImportFrom, ast.Import))]
        rest = [stat for stat in tree.body if not(isinstance(stat, (ast.ImportFrom, ast.Import)))]
        # store ast with import statements
        # can be executed later using: exec(self.import_bytecode)
        self.import_bytecode = compile(ast.Module(imports), '', mode='exec')   
        tree = ast.Module(rest)      
        # look for a with statement with a string, store context info and remove with statement
        tree = self.process_with(tree)                    
        # check that last line is an expression
        expression = tree.body[-1]
        if not(isinstance(expression, ast.Expr)):
            raise ValueError('The following script should finish by an expression: %s' % self.script)      
        # store what is left          
        self.main_ast = tree             
        """
        second find column names in the main code so as to determine what context is used and check coherence
        """
        # find the list of the names of the variables in the main ast 
        visitor = nameVisitor() # see definition of this class below
        visitor.visit(self.main_ast)
        names = set(visitor.names)
        #FIXME could add a check that all names correspond either to a bound variable or is in self.columns
        # need a way to get a list of unbound variable ????
        # then would raise ValueError('There are unbound variables in script %s' % self.script)
        # For now: just consider that the inputs are the intersection of the element of names and of self.columns 
        #FIXME document that this means that using local variables with the same name as db_columns in the scripts will affect the synopsis of the dbfun ...
        self.input_names = list(names.intersection(self.columns))           
        """
        third parse final expression and additional code asts for nodes that involve aliases of the aux_files, get the hierarchy of calls
        to aux_files, check that it is flat, compile the corresponding partial bytecodes and collect all the info necessary for efficient evaluation of the code
        """
        if self.aux_functions:
            connector = lookuptable_connector.LookupTableConnector(self.script, self.aliases)
            connector.visit(self.main_ast)
            # self.code_nodes contains a list of dictionaries containing the info for the various calls to function defined in auxiliary h5 files
            # each dictionry contains entries: 'child_asts', 'varname' and 'function' and optionnally 'output_cols'
            self.code_nodes = self.main_ast.code_nodes
            # clean the main ast
            del(self.main_ast.code_nodes)
        else:
            self.code_nodes = []
        # compile all asts, with final expr apart
        self.final_ast = ast.Expression(self.main_ast.body[-1].value) # without the .value you only get a ast.Expr instead of getting the actual expr
        self.main_ast.body = self.main_ast.body[:-1]
        for dico in self.code_nodes:
            bytecodes = []
            for child in dico['child_asts']:
                bytecodes.append(compile(child, '', mode='eval'))
            dico['child_bytecodes'] = bytecodes
        self.main_bytecode = compile(self.main_ast, '', mode='exec')
        self.final_bytecode = compile(self.final_ast, '', mode='eval')
        

    # just an auxiliary function for parse, dealing with 'with h5file' statements
    def process_with(self, tree):
        self.aux_files = []
        self.aliases = [] 
        self.aux_functions = []                 
        withs = [stat for stat in tree.body if isinstance(stat, ast.With)]
        kept = []        
        for i, w in enumerate(withs):
            if isinstance(w.context_expr, ast.Str):
                kept.append((i, w))
        if len(kept) > 1:
            raise ValueError('There is more than one with statement for re-using auxiliary ABX files in script: %s' % self.script)
        if len(kept) == 1:
            # find the h5 files and aliases            
            s = kept[0][1]                        
            while isinstance(s, ast.With) and isinstance(w.context_expr, ast.Str):
                self.aux_files.append(s.context_expr.s)
                self.aliases.append(s.optional_vars.id)
                s = s.body[0]
            # remove with statement from ast
            stats = []
            with_i = 0
            for stat in tree.body:
                if isinstance(stat, ast.With):
                    if with_i == kept[0][0]:
                        stats.append(s)
                    else:
                        stats.append(stat)
                    with_i = with_i+1
                else:
                    stats.append(stat)
            tree = ast.Module(stats)
            # instantiate corresponding DBfun_LookupTables:           
            for f in self.aux_files:
                self.aux_functions.append(dbfun_lookuptable.DBfun_LookupTable(f, indexed=False))
        return tree

            
    def get_indexes(self):
        return [], {}
        
                
    # function for evaluating the column function given data for the context 
    # context is a dictionary with just the right name/content associations
    def evaluate(self, context):
        # set up context
        ns_local = context
        ns_global = {}
        # exec imports in that context
        exec(self.import_bytecode, ns_global, ns_local)
        # evaluate the calls to aux functions
        for node in self.code_nodes:
            # evaluate the arguments to the call
            aux_context = {}
            args = node['function'].in_names
            for code, arg in zip(node['child_bytecodes'], args):
                aux_context[arg] = eval(code, ns_global, ns_local)
            # call the aux function and assign it in the main namespace
            ns_local[node['varname']] = node['function'].evaluate(aux_context) 
            #FIXME if aux files, could use the output_cols here ? and maybe need to do it also in direct case for consistency ?
            # also is output format for vlen output going to work ?
        # exec main_bytecode 
        exec(self.main_bytecode, ns_global, ns_local)
        return eval(self.final_bytecode, ns_global, ns_local)  


# visitor class for getting the list of the names of the variables in expr (minus the import statements)   
class nameVisitor(ast.NodeVisitor):  
    
    def __init__(self, *args, **kwargs):
        ast.NodeVisitor.__init__(self, *args, **kwargs)  
        self.names = []       
    
    def visit_Name(self, node):
        self.names.append(node.id)