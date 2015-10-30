# -*- coding: utf-8 -*-
"""
Created on Thu May  8 04:07:43 2014

@author: Thomas Schatz
"""

import h5py
import numpy as np
import pandas
import multiprocessing
import os
import time
import traceback
import sys
import warnings
import pickle
try:
    import h5features
except ImportError:
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__))))), 'h5features'))
    import h5features

# FIXME Enforce single process usage when using python compiled with OMP
# enabled

# FIXME detect when multiprocessed jobs crashed
# FIXME do a separate functions: generic load_balancing
# FIXME write distances in a separate file


def create_distance_jobs(pair_file, distance_file, n_cpu):
    # FIXME check (given an optional checking function)
    # that all features required in feat_dbs are indeed present in feature
    # files

    # getting 'by' datasets characteristics
    with h5py.File(pair_file) as fh:
        # by_dsets = [by_dset for by_dset in fh['feat_dbs']]
        by_dsets = fh['bys'][...]
        by_n_pairs = []  # number of distances to be computed for each by db
        for by_dset in by_dsets:
            attrs = fh['unique_pairs'].attrs[by_dset]
            by_n_pairs.append(attrs[2] - attrs[1])
            total_n_pairs = fh['unique_pairs/data'].shape[0]
    # initializing output datasets
    with h5py.File(distance_file) as fh:
        fh.attrs.create('done', False)
        g = fh.create_group('distances')
        g.create_dataset('data', shape=(total_n_pairs, 1), dtype=np.float)
    """
    #### Load balancing ####
    Heuristic: each process should have approximately
    the same number of distances to compute.
        1 - 'by' blocks bigger than n_pairs/n_proc are divided into blocks
            of size n_pairs/n_proc + a remainder block
        2 - iteratively the cpu with the lowest number of distances gets
            attributed the biggest remaining block
    This will not be a good heuristic if the average time required to compute
    a distance varies widely from one 'by' dataset to another or if the i/o
    time is larger than the time required to compute the distances.
    """
    # step 1
    by_n_pairs = np.int64(by_n_pairs)
    total_n_pairs = np.sum(by_n_pairs)
    max_block_size = np.int64(np.ceil(total_n_pairs / np.float(n_cpu)))
    by = []
    start = []
    stop = []
    n_dist = []
    for n_pairs, dset in zip(by_n_pairs, by_dsets):
        sta = 0
        sto = 0
        while n_pairs > 0:
            if n_pairs > max_block_size:
                amount = max_block_size
            else:
                amount = n_pairs
            n_pairs = n_pairs - amount
            sto = sto + amount
            by.append(dset)
            start.append(sta)
            stop.append(sto)
            n_dist.append(amount)
            sta = sta + amount
    # step 2
    # blocks are sorted according to the number of distances they contain
    # (in decreasing order, hence the [::-1])
    order = np.argsort(np.int64(n_dist))[::-1]
    # associated cpu for each block in zip(by, start, stop, n_dist)
    cpu = np.zeros(len(by), dtype=np.int64)
    cpu_loads = np.zeros(n_cpu, dtype=np.int64)
    for i in order:
        idlest_cpu = np.argmin(cpu_loads)
        cpu[i] = idlest_cpu
        cpu_loads[idlest_cpu] = cpu_loads[idlest_cpu] + n_dist[i]
    # output job description for each cpu
    by = np.array(by)  # easier to index...
    start = np.array(start)
    stop = np.array(stop)
    jobs = []
    for i in range(n_cpu):
        indices = np.where(cpu == i)[0]
        _by = list(by[indices])
        _start = start[indices]
        _stop = stop[indices]
        job = {'pair_file': pair_file, 'by': _by,
               'start': _start, 'stop': _stop}
        jobs.append(job)
    return jobs

"""
If there are very large by blocks, two additional
things could help optimization:
    1. doing co-clustering inside of the large by blocks
        at the beginning to get two types of blocks:
        sparse and dense distances (could help if i/o is a problem
        but a bit delicate)
    2. rewriting the features to accomodate the co-clusters
If there are very small by blocks and i/o become too slow
could group them into intermediate size h5features files
"""

"""
This function can be used concurrently by several processes.
When it is the case synchronization of the writing operations in
the target distance_file is required by HDF5.
The current solution uses a global lock for the whole file.
Since each job is writing in different places, it should in principle be
possible to do all the write concurrently if ever necessary, using parallel
HDF5 (based on MPI-IO).
"""


def run_distance_job(job_description, distance_file, distance,
                     feature_files, feature_groups, splitted_features,
                     job_id, distance_file_lock=None):
    if distance_file_lock is None:
        synchronize = False
    else:
        synchronize = True
    if not(splitted_features):
        times = {}
        features = {}
        for feature_file, feature_group in zip(feature_files, feature_groups):
            t, f = h5features.read(feature_file, feature_group)
            assert not(set(times.keys()).intersection(
                t.keys())), ("The same file is indexed by (at least) two "
                             "different feature files")
            times.update(t)
            features.update(f)
        get_features = Features_Accessor(times, features).get_features_from_raw
    pair_file = job_description['pair_file']
    n_blocks = len(job_description['by'])
    for b in range(n_blocks):
        print('Job %d: computing distances for block %d on %d' % (job_id, b,
                                                                  n_blocks))
        # get block spec
        by = job_description['by'][b]
        start = job_description['start'][b]
        stop = job_description['stop'][b]
        if splitted_features:
            # FIXME modify feature_file/feature_group to adapt to 'by'
            # FIXME any change needed when several feature files before
            # splitting ?
            times = {}
            features = {}
            for feature_file, feature_group in zip(feature_files,
                                                   feature_groups):
                t, f = h5features.read(feature_file, feature_group)
                assert not(set(times.keys()).intersection(
                    t.keys())), ("The same file is indexed by (at least) two "
                                 "different feature files")
                times.update(t)
                features.update(f)
            accessor = Features_Accessor(times, features)
            get_features = accessor.get_features_from_splitted
        # load pandas dataframe containing info for loading the features
        store = pandas.HDFStore(pair_file)
        by_db = store['feat_dbs/' + by]
        store.close()
        # load pairs to be computed
        # indexed relatively to the above dataframe
        with h5py.File(pair_file) as fh:
            attrs = fh['unique_pairs'].attrs[by]
            pair_list = fh['unique_pairs/data'][attrs[1]+start:attrs[1]+stop, 0]
            base = attrs[0]

        A = np.mod(pair_list, base)
        B = pair_list // base
        pairs = np.column_stack([A, B])
        n_pairs = pairs.shape[0]
        # get dataframe with one entry by item involved in this block
        # indexed by its 'by'-specific index
        by_inds = np.unique(np.concatenate([A, B]))
        items = by_db.iloc[by_inds]
        # get a dictionary whose keys are the 'by' indices
        features = get_features(items)
        dis = np.empty(shape=(n_pairs, 1))
        # FIXME: second dim is 1 because of the way it is stored to disk,
        # but ultimately it shouldn't be necessary anymore
        # (if using axis arg in np2h5, h52np and h5io...)
        for i in range(n_pairs):
            dataA = features[pairs[i, 0]]
            dataB = features[pairs[i, 1]]
            if dataA.shape[0] == 0:
                warnings.warn('No features found for file {}, {} - {}'
                              .format(items['file'][pairs[i, 0]],
                                      items['onset'][pairs[i, 0]],
                                      items['offset'][pairs[i, 0]]),
                              UserWarning)
            if dataB.shape[0] == 0:
                warnings.warn('No features found for file {}, {} - {}'
                              .format(items['file'][pairs[i, 1]],
                                      items['onset'][pairs[i, 1]],
                                      items['offset'][pairs[i, 1]]),
                              UserWarning)
            try:
                dis[i, 0] = distance(dataA, dataB)
            except:
                sys.stderr.write(
                    'Error when calculating the distance between item {}, {} - {} '
                    'and item {}, {} - {}\n'
                    .format(items['file'][pairs[i, 0]],
                            items['onset'][pairs[i, 0]],
                            items['offset'][pairs[i, 0]],
                            items['file'][pairs[i, 0]],
                            items['onset'][pairs[i, 0]],
                            items['offset'][pairs[i, 0]]),
                )
                raise
        if synchronize:
            distance_file_lock.acquire()
        with h5py.File(distance_file) as fh:
            fh['distances/data'][attrs[1]+start:attrs[1]+stop, :] = dis
        if synchronize:
            distance_file_lock.release()


# mem in megabytes
# FIXME allow several feature files?
# and/or have an external utility for concatenating them?
# get rid of the group in feature file (never used ?)
def compute_distances(feature_file, feature_group, pair_file, distance_file,
                      distance, n_cpu=None, mem=1000,
                      feature_file_as_list=False):
    with h5py.File(distance_file) as fh:
        fh.attrs.create('distance', pickle.dumps(distance))

    if n_cpu is None:
        n_cpu = multiprocessing.cpu_count()
    if not(feature_file_as_list):
        feature_files = [feature_file]
        feature_groups = [feature_group]
    else:
        feature_files = feature_file
        feature_groups = feature_group
    # FIXME if there are other datasets in feature_file this is not accurate
    mem_needed = 0
    for feature_file in feature_files:
        feature_size = os.path.getsize(feature_file) / float(2 ** 20)
        mem_needed = feature_size * n_cpu + mem_needed
    splitted_features = False
    #splitted_features = mem_needed > mem
    # if splitted_features:
    #    split_feature_file(feature_file, feature_group, pair_file)
    jobs = create_distance_jobs(pair_file, distance_file, n_cpu)
    results = []
    if n_cpu > 1:
        # use of a manager seems necessary because we're using a Pool...
        distance_file_lock = multiprocessing.Manager().Lock()
        pool = multiprocessing.Pool(n_cpu)
        try:
            for i, job in enumerate(jobs):
                print('launching job %d' % i)
                # hack to get details of exceptions in child processes
                worker = print_exception(run_distance_job)
                result = pool.apply_async(worker,
                                          (job, distance_file, distance,
                                           feature_files, feature_groups,
                                           splitted_features,
                                           i, distance_file_lock))
                results.append(result)
                time.sleep(10)
            pool.close()
            # wait for results
            # using 'get' allow detecting exceptions in child processes
            finished_jobs = [False] * len(jobs)
            while not(all(finished_jobs)):
                for i, result in enumerate(results):
                    try:
                        result.get(1)  # wait 1 second
                        finished_jobs[i] = True
                    except multiprocessing.TimeoutError:
                        pass
        finally:
            pool.close()  # in case it wasn't done before
            # recommended in multiprocessing doc to avoid zombie process (?)
            pool.join()
            if all(finished_jobs):
                with h5py.File(distance_file) as fh:
                    fh.attrs.modify('done', True)
    else:
        run_distance_job(jobs[0], distance_file, distance,
                         feature_files, feature_groups, splitted_features, 1)
        with h5py.File(distance_file) as fh:
            fh.attrs.modify('done', True)


# hack to get details of exceptions in child processes
# FIXME use as a decorator?
class print_exception(object):

    def __init__(self, fun):
        self.fun = fun

    def __call__(self, *args, **kwargs):
        try:
            return self.fun(*args, **kwargs)
        except Exception:
            print(traceback.format_exc())
            raise


class Features_Accessor(object):

    def __init__(self, times, features):
        self.times = times
        self.features = features

    def get_features_from_raw(self, items):
        features = {}
        for ix, f, on, off in zip(items.index, items['file'],
                                  items['onset'], items['offset']):
            t = np.where(np.logical_and(self.times[f] >= on,
                                        self.times[f] <= off))[0]
            # if len(t) == 0:
            #     raise IOError('No features found for file {}, at '
            #                   'time {}-{}'.format(f, on, off))
            features[ix] = self.features[f][t, :]
        return features

    def get_features_from_splitted(self, items):
        features = {}
        for ix, f, on, off in zip(items.index, items['file'],
                                  items['onset'], items['offset']):
            features[ix] = self.features[f + '_' + str(on) + '_' + str(off)]
        return features

# write split_feature_file, such that it create the appropriate files
# + check that no filename conflict can occur in:
# (f + '_' + str(on) + '_' + str(off))
# -> mem -> mem_by_cpu
# if not enough mem_by_cpu to load whole dataset:
# rewrite files of size matching mem_by_cpu using the structure of the jobs
# do not rewrite items of a by block if not used in considered job
# only way this can fail is if some (sub-)by blocks contain too many items for
# being stored in mem_by_cpu
# do not treat this case for now, but detect it and if it ever happens:
#   divide items in (items_1, items_2,....)
#   read items_1, then items_1, items_2, then items_1, items_3...
# if this ever proves too slow: could use co-clustering on the big by blocks,
# use it for the job creation and adopt smarter loading schemes

if __name__ == '__main__':

    import argparse
    import metrics.cosine as cosine
    import metrics.dtw as dtw

    def dtw_cosine_distance(x, y):
        return dtw.dtw(x, y, cosine.cosine_distance)

    # parser (the usage string is specified explicitly because the default
    # does not show that the mandatory arguments must come before the
    # mandatory ones; otherwise parsing is not possible beacause optional
    # arguments can have various numbers of inputs)
    parser = argparse.ArgumentParser(usage="%(prog)s features task [distance]"
                                           " [-o output]",
                                     description='ABX distance computation')
    # I/O files
    g1 = parser.add_argument_group('I/O files')
    g1.add_argument('features', help='feature file')
    g1.add_argument('task', help='task file generated by the task module, \
        containing the triplets and the pairs associated to the task \
        specification')
    g1.add_argument('distance', nargs='?', default=None,
                    help='optional, callable: distance to use')
    g1.add_argument(
        '-o', '--output', help='optional: output distance file')
    g1.add_argument(
        '-n', '--ncpu', default=None, help='optional: number of cpus to use')
    args = parser.parse_args()
    compute_distances(args.features, '/features/', args.task,
                      args.output, dtw_cosine_distance, n_cpu=args.ncpu)
