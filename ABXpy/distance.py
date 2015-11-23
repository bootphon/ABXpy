import argparse
import os
import sys

from ABXpy.distances import distances
from ABXpy.distances.example_distances import dtw_cosine


def default_distance(x, y):
    """ Dynamic time warping cosine distance

    The "feature" dimension is along the columns and the "time" dimension
    along the lines of arrays x and y
    """
    return dtw_cosine(x, y)


def run(features, task, output, distance=None, jobs=1):
    jobs = int(jobs)
    if distance:
        distancepair = distance.split('.')
        distancemodule = distancepair[0]
        distancefunction = distancepair[1]
        path, mod = os.path.split(distancemodule)
        sys.path.insert(0, path)
        distancefun = getattr(__import__(mod), distancefunction)
    else:
        distancefun = default_distance

    distances.compute_distances(features, '/features/', task,
                                output, distancefun, n_cpu=jobs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Compute distances for the ABX discrimination task')
    parser.add_argument(
        'features', help='h5features file containing the feature to evaluate')
    parser.add_argument(
        'task', help='task file')
    parser.add_argument(
        'output', help='output file for distance pairs')
    parser.add_argument(
        '-d', '--distance',
        help='distance module to use (distancemodule.distancefunction, '
        'default to dtw cosine distance',
        metavar='distancemodule.distancefunction')
    parser.add_argument(
        '-j', '--jobs',
        help='number of cpus to use',
        type=int, default=1)

    args = parser.parse_args()
    run(args.features, args.task, args.output,
        distance=args.distance, jobs=args.jobs)
