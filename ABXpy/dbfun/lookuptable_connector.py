# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 02:25:17 2013

@author: Thomas Schatz
"""

"""
AST visitor class for finding calls to lookup table (.dbfun) files in a script and make the script ready for execution.

There is a restriction: when in a lookup table calling node, check that the node.code_nodes concatened of the children is empty: i.e. hierarchical calls to auxiliary h5 file
are not allowed with a depth larger than 1. We could allow deeper calls, but would there be any practical benefit ? Probably not because the input to a lookup table 
call can only be of the type of a column of the database (at least with the current system).
"""

import ast, uuid

class LookupTableConnector(ast.NodeTransformer):
    
    def __init__(self, script, aux_functions, aliases, *args, **kwargs):
        ast.NodeTransformer.__init__(self, *args, **kwargs)
        self.aux_functions = aux_functions 
        self.aliases = aliases
        self.script = script
     
     
    def check_Call(self, node):
        if not(isinstance(node.func.ctx, ast.Load) and not(node.keywords) and node.kwargs is None and node.starargs is None):
                raise ValueError('Call to function %s defined in an auxiliary h5 file is not correct in script: %s' % (node.func.id, self.script))


    def check_Subscript(self, node, func_name):
        error = ValueError('Call to function %s defined in an auxiliary h5 file is not correct in script: %s' % (func_name, self.script))
        if not(isinstance(node.slice, ast.Index) and isinstance(node.ctx, ast.Load)):
            raise error
        if not(isinstance(node.slice.value, ast.Tuple) and isinstance(node.slice.value.ctx, ast.Load)):
            raise error
        # output column must appear explicitly as strings
        if not(all([isinstance(e, ast.Str) for e in node.slice.value.elts])):
            raise error


    def check_flatness(self, node):
        if node.code_nodes:
            raise ValueError('There are calls to functions defined in auxiliary files whose arguments are defined in terms of calls to other functions defined in auxiliary files in script: %s' % self.script)
      
    
    # extract and store in a code_node all useful information about the call
    # and replace node in its parent by a ast.Name node pointing to a random but duly stored 'varname'    
    def bundle_call_info(self, node, call_node):      
        code_node = {}
        if not(node is call_node):
            code_node['output_cols'] = [e.s for e in node.slice.value.elts]
        code_node['child_asts'] = [ast.Expression(arg) for arg in node.args]
        code_node['function'] = self.aux_functions(self.aliases.index(call_node.func.id))
        code_node['varname'] = 'var_' + str(uuid.uuid4()).translate(None, '-')                        
        new_node = ast.copy_location(ast.Name(ctx=ast.Load(), id=code_node['varname']), node)
        new_node.code_nodes = [code_node]
        return new_node  
        
      
    # case of call with output columns specified: aux_file_alias(in_1, ..., in_k).out['out_name_1',..., 'out_name_n']   
    def visit_Subscript(self, node):
        # check if it is a call to an auxiliary h5 file        
        aux_call = False        
        if isinstance(node.value, ast.Attribute) and node.value.attr == 'out':
            call_node = node.value.value
            if isinstance(call_node, ast.Call) and call_node.func.id in self.aliases:
                aux_call = True
        if not(aux_call):
            # visit all children and bubble up code_nodes
            node = self.generic_visit(node)
            return node
        else:
            # first check correctness of the call
            self.check_Call(call_node)
            self.check_Subscript(node, call_node.func.id)
            # check that the aux function call is flat (i.e. there are no other aux function call in the call_node children)            
            call_node = self.generic_visit(call_node) # generic visit here, not visit_Call, to bubble up code_nodes            
            node.code_nodes = call_node.code_nodes
            self.check_flatness(node) 
            # extract and store in a code_node all useful information about the call
            # and replace node in its parent by a ast.Name node pointing to a random but duly stored 'varname'
            return self.bundle_call_info(node, call_node)            

                 
    # case of call for all outputs: aux_file_alias(in_1, ..., in_k)
    def visit_Call(self, node):
        # check if it is not a call to an auxiliary h5 file                
        if not(node.func.id in self.aliases):
            # visit all children and bubble up code_nodes
            node = self.generic_visit(node)
            return node 
        else:
            # first check correctness of the call
            self.check_Call(node)
            # check that the aux function call is flat (i.e. there are no other aux function call in the node children)            
            node = self.generic_visit(node) # bubble up code nodes      
            self.check_flatness(node) 
            return self.bundle_call_info(node, node)           
            
        
    def generic_visit(self, node):
        # visit all children
        super(ast.NodeVisitor, self).generic_visit(node)
        # bubble up code_nodes from the children if any (cleaning up children at the same time to keep sound asts)
        node.code_nodes = []
        for child in ast.iter_child_nodes(node):
            node.code_nodes = node.code_nodes + child.code_nodes
            del(child.code_nodes)# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 02:25:17 2013

@author: Thomas Schatz
"""

"""
AST visitor class for finding calls to lookup table (.dbfun) files in a script
and make the script ready for execution.

There is a restriction: when in a lookup table calling node, check that the
node.code_nodes concatened of the children is empty: i.e. hierarchical calls to
auxiliary h5 file are not allowed with a depth larger than 1. We could allow
deeper calls, but would there be any practical benefit ? Probably not because
the input to a lookup table call can only be of the type of a column of the
database (at least with the current system).
"""

import ast
import uuid


class LookupTableConnector(ast.NodeTransformer):

    def __init__(self, script, aux_functions, aliases, *args, **kwargs):
        ast.NodeTransformer.__init__(self, *args, **kwargs)
        self.aux_functions = aux_functions
        self.aliases = aliases
        self.script = script

    def check_Call(self, node):
        if not(isinstance(node.func.ctx, ast.Load) and not(node.keywords) and
               node.kwargs is None and node.starargs is None):
            raise ValueError(
                'Call to function %s defined in an auxiliary h5 file is not '
                'correct in script: %s' % (
                node.func.id, self.script))

    def check_Subscript(self, node, func_name):
        error = ValueError(
            'Call to function %s defined in an auxiliary h5 file is not '
            'correct in script: %s' % (
            func_name, self.script))
        if not(isinstance(node.slice, ast.Index) and
               isinstance(node.ctx, ast.Load)):
            raise error
        if not(isinstance(node.slice.value, ast.Tuple) and
               isinstance(node.slice.value.ctx, ast.Load)):
            raise error
        # output column must appear explicitly as strings
        if not(all([isinstance(e, ast.Str) for e in node.slice.value.elts])):
            raise error

    def check_flatness(self, node):
        if node.code_nodes:
            raise ValueError(
                'There are calls to functions defined in auxiliary files whose'
                ' arguments are defined in terms of calls to other functions'
                ' defined in auxiliary files in script: %s' % self.script)

    # extract and store in a code_node all useful information about the call
    # and replace node in its parent by a ast.Name node pointing to a random
    # but duly stored 'varname'
    def bundle_call_info(self, node, call_node):
        code_node = {}
        if not(node is call_node):
            code_node['output_cols'] = [e.s for e in node.slice.value.elts]
        code_node['child_asts'] = [ast.Expression(arg) for arg in node.args]
        code_node['function'] = self.aux_functions(
            self.aliases.index(call_node.func.id))
        code_node['varname'] = 'var_' + str(uuid.uuid4()).translate(None, '-')
        new_node = ast.copy_location(
            ast.Name(ctx=ast.Load(), id=code_node['varname']), node)
        new_node.code_nodes = [code_node]
        return new_node

    # case of call with output columns specified: aux_file_alias(in_1, ...,
    # in_k).out['out_name_1',..., 'out_name_n']
    def visit_Subscript(self, node):
        # check if it is a call to an auxiliary h5 file
        aux_call = False
        if isinstance(node.value, ast.Attribute) and node.value.attr == 'out':
            call_node = node.value.value
            if ((isinstance(call_node, ast.Call) and
                 call_node.func.id in self.aliases)):
                aux_call = True
        if not(aux_call):
            # visit all children and bubble up code_nodes
            node = self.generic_visit(node)
            return node
        else:
            # first check correctness of the call
            self.check_Call(call_node)
            self.check_Subscript(node, call_node.func.id)
            # check that the aux function call is flat (i.e. there are no other
            # aux function call in the call_node children)
            # generic visit here, not visit_Call, to bubble up code_nodes
            call_node = self.generic_visit(call_node)
            node.code_nodes = call_node.code_nodes
            self.check_flatness(node)
            # extract and store in a code_node all useful information about the
            # call and replace node in its parent by a ast.Name node pointing
            # to a random but duly stored 'varname'
            return self.bundle_call_info(node, call_node)

    # case of call for all outputs: aux_file_alias(in_1, ..., in_k)
    def visit_Call(self, node):
        # check if it is not a call to an auxiliary h5 file
        if not(node.func.id in self.aliases):
            # visit all children and bubble up code_nodes
            node = self.generic_visit(node)
            return node
        else:
            # first check correctness of the call
            self.check_Call(node)
            # check that the aux function call is flat (i.e. there are no other
            # aux function call in the node children)
            node = self.generic_visit(node)  # bubble up code nodes
            self.check_flatness(node)
            return self.bundle_call_info(node, node)

    def generic_visit(self, node):
        # visit all children
        super(ast.NodeVisitor, self).generic_visit(node)
        # bubble up code_nodes from the children if any (cleaning up children
        # at the same time to keep sound asts)
        node.code_nodes = []
        for child in ast.iter_child_nodes(node):
            node.code_nodes = node.code_nodes + child.code_nodes
            del(child.code_nodes)
