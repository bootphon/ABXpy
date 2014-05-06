# -*- coding: utf-8 -*-
"""
Created on Wed Mar 12 01:23:01 2014

@author: Thomas Schatz
"""


import h5py, pandas
import numpy as np

#FIXME write distances into a separate file + accept files provided externally
#FIXME what about accepting incomplete file
#FIXME and a utility for creating the outside file (maybe dbfun_table_lookup does it?)


# this function does the load balancing between different processes and prepares the computing environment for each process
def setup_distance_computation(pair_file, distance_file, n_cpu):
       
    with h5py.File(pair_file) as fh:
        by_dsets = [by_dset for by_dset in fh['unique_pairs']]
        l = [] # number of distances to be computed for each by db
        for by_dset in by_dsets:
            l.append(fh['unique_pairs'][by_dset].shape[0])
    with h5py.File(distance_file) as fh: # prepare output datasets
        g = fh.create_group('distances')
        for n, by_dset in zip(l, by_dsets):
            g.create_dataset(by_dset, shape=(n,1), dtype=np.float)
    # very simple load balancing for now: one or more process per by if enough cpu
    if n_cpu <= len(l): # less than one cpu per by        
        return zip(by_dsets, [None]*len(by_dsets), [None]*len(by_dsets)) # list of by, start_i and end_i 
    else:
        n_cpu*np.array(l)/np.sum(l)
        p = np.int64(np.ceil(np.array(n_cpu*l/sum(l))))
        assert np.all(p>0) #FIXME this create more processes than there are cpus ...
        bys = []
        start_is = []
        end_is = []
        for e, b, n in zip(p, by_dsets, l):
            bys = bys+e*[b]
            ind = np.linspace(0, n-1, e+1)
            end_is =  end_is + ind[1:]
            start_is = start_is + ind[:-1]
        return zip(bys, start_is, end_is)
    #FIXME memory constraints are just ignored for now
    #FIXME allow fusioning small by together
 
# this function is called by each process to carry out actual distance computations
def compute_distances(load_f, dis_f, pair_file, distance_file, by, start_i=None, end_i=None):
    
    # load distance list (supposed to fit into memory here...) and by db
    with h5py.File(pair_file) as fh:
        if start_i == None: start_i = 0
        if end_i == None: end_i = fh['unique_pairs/'+ by].shape[0]+1
        pair_list = fh['unique_pairs/'+ by][start_i:end_i,0]
        base = fh['unique_pairs'].attrs[by]
    store = pandas.HDFStore(pair_file) #FIXME interaction of pyTable and h5py gives weird error messages ...
    db = store['feat_dbs/' + by]
    store.close()        
    # decode distance pairs
    A = np.mod(pair_list, base)
    B = pair_list // base
    frameA = db.iloc[A]
    frameB = db.iloc[B]   
    # do a big naive for loop:
    d = np.empty(shape=(len(frameA),1))
    # load data
    df = pandas.concat([frameA, frameB])
    df['index'] = df.index
    df.drop_duplicates(cols='index', inplace=True)
    df = df.drop('index', axis=1)
    features = load_f(df) # returns a dictionary with the dataframe index as key 
    print('computing %d distances for by level %s' % (len(frameA), by))
    for i in range(len(frameA)): 
        #print('computing distance  %d on %d for by level %s' % (i, len(frameA), by))
        dataA = features[frameA.index[i]]
        dataB = features[frameB.index[i]]
        d[i,0] = dis_f(dataA, dataB)
    with h5py.File(distance_file) as fh:
        fh['distances/' + by][start_i:end_i,:] = d # must have been prepared