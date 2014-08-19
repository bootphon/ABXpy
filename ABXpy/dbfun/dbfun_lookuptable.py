# -*- coding: utf-8 -*-
"""
Created on Mon Nov 25 00:24:42 2013

@author: Thomas Schatz

Implements the DBfun API
Basic implementation of database function in lookup tables.
Allows on-the-fly computation by storing script for DBfun_compute alongside the table.
Allows to store outputs with h5 compatible dtypes either directly or under an indexed format
Do not implement variable length outputs and requires that the entire lookup table fits in RAM memory. 
"""

# make sure the rest of the ABXpy package is accessible
import os, sys
package_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
if not(package_path in sys.path):
    sys.path.append(package_path)
import ABXpy.misc.type_fitting as type_fitting 
#FIXME should remove above dependency on rest of ABX...

import h5py, numpy, operator, collections 
import dbfun, dbfun_compute


#FIXME when data is missing: potentially use DB_column ?
#FIXME make sure extension for other kind of input/output is easy: maybe use class for i/o as well ?
#FIXME h5 file locking and db path and md5 hash storing...
#FIXME string processing in the rest of the code is inconsistent and might cause problem for a python 3 version: there are two types of strings str and unicode, I should go back through all the code and check whether it is compatible with unicode, plus what about pandas ? in particular isinstance(s, str) is problematic since it evaluates to false for unicode strings...                   
# should be replaced by isinstance(s, (str, unicode))
class DBfun_LookupTable(dbfun.DBfun): 

    
    # if indexed is False, evaluate will return actual values instead of just indexes
    def __init__(self, filename, synopsis=None, db=None, code=None, indexed=True):
        
        try:
            with open(filename):
                if not(synopsis is None):
                    raise ValueError('File %s already exists' % filename)  
        except IOError: # if file doesn't exist create it 
            with h5py.File(filename) as f:
                f.attrs['is_empty'] = True                
                f.attrs['is_sorted'] = False
                f.attrs['indexed'] = indexed
                if not(code is None):
                    f.attrs['code'] = unicode(code)
                # synopsis
                str_dtype = h5py.special_dtype(vlen=unicode) # h5 dtype for storing variable length strings
                g = f.create_group('synopsis')               
                g.create_dataset('in_names', data=synopsis['in_names'], dtype=str_dtype)
                g.create_dataset('out_names', data=synopsis['out_names'], dtype=str_dtype)
                in_types = synopsis['in_types']  # could try to do inference from in_names if possible ...
                # check that types are column names from db
                if not(set(in_types).issubset(db.columns)):
                    raise ValueError('Not all input types in %s match a column name from %s' % (in_types, db.columns))
                g.create_dataset('in_types', data=synopsis['in_types'], dtype=str_dtype)
                # get input indexes from db
                index_group = g.create_group('indexes')
                types = set(synopsis['in_types'])
                indexes = {}
                for t in types:
                    index = list(set(db[t]))
                    index.sort()
                    index_group.create_dataset(t, data=index, dtype=get_dtype(index))
                    indexes[t] = index
                # get number of levels for the input key and check that it remains managable
                in_nb_levels = [len(indexes[t]) for t in in_types]
                max_key = reduce(operator.mul, in_nb_levels, 1)-1
                if max_key >= 2**64:
                    raise ValueError('lookup table in file %s cannot be created because 64 bits keys are not sufficient to cover all possible combinations of the inputs' % filename)
                g.create_dataset('in_nb_levels', data=in_nb_levels, dtype=numpy.uint64)                
                # optional elements of synopsis           
                if synopsis.has_key('indexed_outputs'):
                    g.create_dataset('indexed_outputs', data=synopsis['indexed_outputs'], dtype=str_dtype)
                    for o in synopsis['indexed_outputs']:
                        index = synopsis['output_indexes'][o]                    
                        index_group.create_dataset(o, data=index, dtype=get_dtype(index))
                # instantiate key datasets and data group
                f.create_dataset('keys', (0,), dtype=numpy.uint64, chunks=(chunk_size(),), maxshape=(None,))
                f.create_group('data')
        # load object from (possibly newly created) file
        self.filename = filename
        self.load()

      
    # instantiate DBfun_LookupTable object from existing .dbfun file
    def load(self):
        self.load_metadata() 
        self.load_data() # this implementation supposes that the lookup table can be held in memory without problems

      
    def load_metadata(self):         
        with h5py.File(self.filename) as f: 
            self.indexed = f.attrs['indexed']
            self.is_empty = f.attrs['is_empty']
            self.is_sorted = f.attrs['is_sorted']
            self.input_names = list(f['synopsis/in_names'][...])
            self.output_names = list(f['synopsis/out_names'][...])
            self.input_types = list(f['synopsis/in_types'][...])
            self.indexes ={}
            for t in self.input_types:
                self.indexes[t] = list(f['synopsis/indexes/%s' % t][...])
            self.in_nb_levels = f['synopsis/in_nb_levels'][...]
            self.key_weights = numpy.concatenate([numpy.array([1], dtype=numpy.uint64), numpy.cumprod(numpy.uint64(self.in_nb_levels))[:-1]])
            self.indexed_outputs = []
            if 'synopsis/indexed_outputs' in f:
                self.indexed_outputs = list(f['synopsis/indexed_outputs'][...])
                if 'synopsis/indexed_outputs_dims' in f:
                    self.indexed_outputs_dims = f['synopsis/indexed_outputs_dims'][...]
                for o in self.indexed_outputs:
                    self.indexes[o] = f['synopsis/indexes/%s' % o][...]
            if 'code' in f: # instantiate dbfun_compute object if there is code
                self.code = f.attrs['code']   
                self.computer = dbfun_compute.DBfun_Compute(self.code, self.input_names)
                if not(self.input_names == self.computer.input_names): #check that all input names are used
                    raise ValueError('Some input columns defined in the synopsis of file %s are unused in the corresponding script %s' % (self.filename, self.code))
          
          
    def load_data(self):
         with h5py.File(self.filename) as f:
            if 'keys' in f and f['keys'].shape[0] > 0:
                self.keys = f['keys'][...] # load keys from file
            if 'data' in f:
                self.data = {}
                for dset in f['data']:                    
                    self.data[dset] = f['data'][dset][...] # load data from file

    
    # possible optimization: grouping datasets for outputs with similar types                 
    def fill(self, data, append=False, iterate=False):
        if not(self.is_empty) and not(append):
            raise IOError('DBfun_LookupTable %s is already filled' % self.filename)
        if self.is_empty: # if necessary, instantiate output datasets                              
            if iterate: 
                sample_data = data.next()    
            else:
                sample_data = data                             
            self.initialize_output_dsets(sample_data)
            if iterate: self.write(sample_data) # store data that was generated 
        # set flags
        with h5py.File(self.filename) as f:
            if self.is_empty:
                self.is_empty = False
                f.attrs['is_empty'] = False                 
            if self.is_sorted:
                self.is_sorted = False
                f.attrs['is_sorted'] = False
        # fill table with data 
        if iterate:
            for d in data:
                self.write(d)
        else:
            self.write(data)
                
    
    def initialize_output_dsets(self, sample_data):
        out = [o if hasattr(o, 'shape') else numpy.array(o) for o in sample_data[1]] # do some automatic conversion (maybe risky?)
        if isinstance(out, collections.Mapping): # dict, DataFrame ...
            dim = [1 if len(out[o_name].shape) == 1 else out[o_name].shape[1] for o_name in self.output_names]
            dtypes = [get_dtype(out[o_name]) for o_name in self.output_names]
        else: # list, tuple ...
            dim = [1 if len(o.shape) == 1 else o.shape[1] for o in out]
            dtypes = [get_dtype(o) for o in out]
        with h5py.File(self.filename) as f:    
            for o, d, t in zip(self.output_names, dim, dtypes):
                if not(o in self.indexed_outputs):
                    f['data'].create_dataset(o, (0,d), dtype=t, chunks=(chunk_size(numpy.dtype(t).itemsize, d), d), maxshape=(None,d))
            indexed_o_dims = []      
            indexed_o_levels = []
            for o in self.indexed_outputs: # indexed outputs are stored in the order specified by self.indexed_outputs
                indexed_o_dims.append(dim[self.output_names.index(o)])
                indexed_o_levels.append(len(self.indexes[o]))
            d = sum(indexed_o_dims)
            t = type_fitting.fit_integer_type(max(indexed_o_levels), is_signed=False) # smallest unsigned integer dtype compatible with all indexed_outputs         
            f['data'].create_dataset('indexed_outputs', (0, d), dtype=t, chunks=(chunk_size(numpy.dtype(t).itemsize, d), d), maxshape=(None,d))            
            f['synopsis'].create_dataset('indexed_outputs_dims', data=numpy.cumsum(indexed_o_dims), dtype=numpy.int64) # necessary to access the part of the dataset corresponding to a particular output                                    

           
    #FIXME use np2h5 buffers to write in the different datasets ? (but requires adapting np2h5 to resizable datasets)
    def write(self, data):
        with h5py.File(self.filename) as f:
            # translate input values to keys and append to table
            keys = self.get_keys(data[0])            
            old_n_lines = f['keys'].shape[0]
            new_n_lines = old_n_lines+keys.shape[0]
            f['keys'].resize((new_n_lines,))
            f['keys'][old_n_lines:new_n_lines] = keys
            # append outputs to table
            if isinstance(data[1], collections.Mapping): # dict, DataFrame ...
                output_values = [data[1][o] for o in self.outputs]
            else: # list, tuple ...
                output_values = data[1]
            output_values = [o if hasattr(o, 'shape') else numpy.array(o) for o in output_values] # some risky type conversion ?
            for o_name, o_value in zip(self.output_names, output_values):
                if not(o_name in self.indexed_outputs):
                    d = f['data'][o_name].shape[1]
                    f['data'][o_name].resize((new_n_lines, d))
                    if d==1 and len(o_value.shape)==1:
                        o_value.resize((o_value.shape[0], 1)) # if this causes speed issues could use 1d datasets in this case...
                    f['data'][o_name][old_n_lines:new_n_lines, :] = o_value 
            indexed_o_values = []
            for o in self.indexed_outputs:
                indexed_o_values.append(output_values[self.output_names.index(o)])    
                #FIXME check that values are in correct range of index 
            indexed_o_value = numpy.concatenate(indexed_o_values, axis=1) 
            d = f['data']['indexed_outputs'].shape[1]
            f['data']['indexed_outputs'].resize((new_n_lines, d))
            if d==1 and len(o_value.shape)==1:
                o_value.resize((o_value.shape[0], 1)) # if this causes speed issues could use 1d datasets in this case...                   
            f['data']['indexed_outputs'][old_n_lines:new_n_lines, :] = indexed_o_value
 
 
    # this function might be optimized if useful (using searchsorted and stuff?)
    def get_keys(self, input_values):
        if isinstance(input_values, collections.Mapping): # dict, DataFrame ...
            indexes = [[self.indexes[i_type].index(e) for e in input_values[i_name]] for i_name, i_type in zip(self.input_names, self.input_types)]
        else: # list, tuple ...
            indexes = [[self.indexes[i_type].index(e) for e in input_values[i]] for i, i_type in enumerate(self.input_types)]
        keys = numpy.sum(self.key_weights*numpy.uint64(indexes).T, axis=1) # this is vectorial
        return keys

     
    #FIXME implement this 
    def compress_index(self, indexed_output_name):
        pass # find index values actually occurring at least once in file, use them as new index, reindex file (all columns indexed by it)


    # assumes the dataset fits in RAM memory
    def pack(self):      
        with h5py.File(self.filename) as f:
            # sort on keys with a H5Handler 
            datasets = [o for o in self.output_names if not(o in self.indexed_outputs)] + ['indexed_outputs'] # datasets containing the outputs (or outputs' index)
            groups = ['data']*len(datasets) # groups of the datasets containing the outputs
            keys = f['keys'][...]
            order = numpy.argsort(keys)
            f['keys'][...] = keys[order]
            #FIXME detect duplicates and fail if any ?
            for g, d in zip(groups, datasets):
                data = f[g +'/'+ d][...] 
                f[g +'/'+ d][...] = data[order]
            # signal that file is sorted
            f.attrs['is_sorted'] = True
            # reload everything to be ready for querying
            self.load()
 
           
    def output_specs(self):
        indexes = {}
        if self.indexed:
            for o in self.indexed_outputs: 
                indexes[o] = numpy.array(self.indexes[o])
        return len(self.output_names), self.output_names, indexes
         
    
    # function for evaluating the DB_Function given data for the context 
    # context is a dictionary with the right input_name/queried_value associations
    # assumes the dataset fits in RAM memory
    #FIXME allow loading of specified outputs only
    def evaluate(self, context):
        
        if not(self.is_sorted):
            raise IOError("Cannot use DBfun_TableLookup object that hasn't been packed (i.e. sorted on keys)")
        # possible optimization: unique on keys: keys, keys_order, keys_back = numpy.unique(keys, return_index=True, return_inverse=True)
        keys = self.get_keys(context) # compute queried keys
        insertion_points = numpy.searchsorted(self.keys, keys) # find insertion points for the keys
        # find missing queries and generate data           
        missing = []
        m = numpy.nonzero(insertion_points == len(self.keys))
        if m[0].size: 
            missing.append(m[0])
        m = numpy.nonzero(self.keys[insertion_points] != keys)
        if m[0].size: 
            missing.append(m[0])
        if missing:
            missing = numpy.concatenate(missing)
        else:
            missing = numpy.empty((0,), dtype=numpy.uint64) # empty array
        if missing.size:
            if hasattr(self, 'code'):
                missing_data = self.computer.evaluate(keys[missing], context) 
                if self.indexed: # re-encode indexed outputs
                    for o in self.indexed_outputs: 
                        ind = self.output_names.index(o)  
                        #FIXME accelerate this with searchsorted
                        index = numpy.array(self.indexes[o])
                        d = numpy.array(shape=missing_data[ind].shape, dtype=index.dtype)
                        for l in range(missing_data[ind].shape[0]):
                            if len(missing_data[ind].shape) > 1:
                                for c in range(missing_data[ind].shape[1]):
                                    d[l, c] =  numpy.where(index == missing_data[ind][l, c])
                            else:
                                d[l] =  numpy.where(index == missing_data[ind][l])
                        missing_data[ind] = d      
            else:
                raise RuntimeError('Missing data in table %s with no code' % self.filename)
        # for other queries get row and load data
        present = numpy.setdiff1d(range(len(keys)), missing) # gives a sorted array
        present_location = insertion_points[present]
        if present.size:
            present_data = []
            for o in self.output_names:
                if not(o in self.indexed_outputs):
                    present_data.append(self.data[o][present_location, :])
                else:
                    present_data.append([]) # just a placeholder
            indexed_o_data = self.data['indexed_outputs'][present_location, :]
            d = 0
            for i, o in enumerate(self.indexed_outputs): 
                next_d = self.indexed_outputs_dims[i] #FIXME: should be cumdims
                ind = self.output_names.index(o)                
                present_data[ind] = indexed_o_data[:,d:next_d]            
                d = next_d
            if not(self.indexed): # de-code indexed outputs
                for o in self.indexed_outputs: 
                    ind = self.output_names.index(o)   
                    index = numpy.array(self.indexes[o])
                    present_data[ind] = index[present_data[ind]]
        # reorder results if needed                       
        if missing.size and present.size:
            order = numpy.argsort(numpy.concatenate(missing, present))
            data = [numpy.concatenate(m_d, p_d)[order,:] for m_d, p_d in zip(missing_data, present_data)] # does this work with one-column outputs ?
        elif present.size:
            data = present_data
        elif missing.size:
            data = missing_data
        return data
        #FIXME give a way to obtain the indexes of indexed_outputs from an external function
        
        
# auxiliary function for determining dtype, strings (unicode or not) are always encoded with a variable length dtype, thus it should be more efficient in general to index string outputs, it's actually mandatory because determining chunk_size would fail for non-indexed strings
def get_dtype(data):
    str_dtype = h5py.special_dtype(vlen=unicode)
    if isinstance(data[0], str) or isinstance(data[0], unicode): # allow for the use of strings
        dtype = str_dtype
    elif hasattr(data, 'dtype'): # could add some checks that the dtype is one of those supported by h5 ?    
        dtype = data.dtype
    else:
        dtype = numpy.array(data).dtype
    return dtype


# item_size given in bytes, size_in_mem given in kilobytes
def chunk_size(item_size=4, n_columns=1, size_in_mem=400):
    return int(round(size_in_mem*1000./(item_size*n_columns)))

    
 