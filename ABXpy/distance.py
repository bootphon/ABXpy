import sys
from ABXpy.distances import distances
import ABXpy.distances.metrics.dtw as dtw
import ABXpy.distances.metrics.cosine as cosine
import argparse
import editdistance
import os
import numpy as np
import warnings


def default_distance(x, y, normalized):
    """ Dynamic time warping cosine distance

    The "feature" dimension is along the columns and the "time" dimension
    along the lines of arrays x and y
    """
    if x.shape[0] > 0 and y.shape[0] > 0:
        # x and y are not empty
        d = dtw.dtw(x, y, cosine.cosine_distance,
                    normalized=normalized)
    elif x.shape[0] == y.shape[0]:
        # both x and y are empty
        d = 0
    else:
        # x or y is empty
        d = np.inf
    return d

def edit_distance(x, y):
    """Levenshtein Distance

    The "feature" dimension is along the columns and the "time" dimension
    along the lines of arrays x and y
    """
    # convert arrays to tuple, to evaluate w/ editdistance
    def totuple(a):
        try:
            return tuple(totuple(i) for i in a)
        except TypeError:
            return a

    if x.shape[0] > 0 and y.shape[0] > 0:
        # x and y are not empty
        d = editdistance.eval(totuple(x), totuple(y))
    elif x.shape[0] == y.shape[0]:
        # both x and y are empty
        d = 0
    else:
        # x or y is empty
        d = np.inf
    return d

def run(features, task, output, normalized,
        distance=None, njobs=1, group='features'):
    njobs = int(njobs)
    if distance:
        if distance=="levenshtein":
            distancefun = edit_distance
        else:
            distancepair = distance.split('.')
            distancemodule = distancepair[0]
            distancefunction = distancepair[1]
            path, mod = os.path.split(distancemodule)
            sys.path.insert(0, path)
            distancefun = getattr(__import__(mod), distancefunction)
    else:
        distancefun = default_distance

    distances.compute_distances(
        features, group, task, output,
        distancefun, normalized=normalized, n_cpu=njobs)


def main():
    parser = argparse.ArgumentParser(
        description='Compute distances for the ABX discrimination task')

    parser.add_argument(
        'features',
        help='h5features file containing the feature to evaluate')

    parser.add_argument(
        '-g', '--group', default='features',
        help='group to read in the h5features file, default is %(default)s')

    parser.add_argument(
        'task', help='task file')

    parser.add_argument(
        'output', help='output file for distance pairs')

    parser.add_argument(
        '-d', '--distance', metavar='distancemodule.distancefunction',
        help='''Define distance module to use.\n\n'''
             '''Use "-d levenshtein" to use the Levenshtein distance'''
             ''' instead of DTW.\n\n'''
             '''Use -d distancemodule.distancefunction to use you own'''
             ''' distance\n\n'''
             '''If not set, it defaults to dtw cosine distance''')

    parser.add_argument(
        '-j', '--njobs', type=int, default=1,
        help='number of cpus to use')

    parser.add_argument(
        '-n', '--normalization', type=int, default=None,
        help='if dtw distance selected, compute with normalization or with '
        'sum. If put to 1 : computes with normalization, if put to 0 : '
        'computes with sum. Common choice is to use normalization (-n 1)')

    args = parser.parse_args()

    if os.path.exists(args.output):
        warnings.warn("Overwriting distance file " + args.output, UserWarning)
        os.remove(args.output)

    # if dtw distance selected, fore use of normalization parameter :
    if (args.distance is None and args.normalization is None):
        sys.exit("ERROR : DTW normalization parameter not specified !")

    run(args.features, args.task, args.output, normalized=args.normalization,
        distance=args.distance, njobs=args.njobs, group=args.group)


if __name__ == '__main__':
    main()
