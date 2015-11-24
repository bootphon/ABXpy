#!/usr/bin/env python
"""Provides a command-line API to ABX.distance"""

import argparse
import os
import sys

from ABXpy.distances import distances
from ABXpy.distances.example_distances import dtw_cosine


def run(features, task, output, distance=None, ncpus=1):
    ncpus = int(ncpus)
    if distance:
        distancepair = distance.split('.')
        distancemodule = distancepair[0]
        distancefunction = distancepair[1]
        path, mod = os.path.split(distancemodule)
        sys.path.insert(0, path)
        distancefun = getattr(__import__(mod), distancefunction)
    else:
        # default distance if unspecified
        distancefun = dtw_cosine

    distances.compute_distances(features, '/features/', task,
                                output, distancefun, n_cpu=ncpus)

def main():
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
        '-n', '--ncpus',
        help='number of cpus to use',
        type=int, default=1)

    args = parser.parse_args()
    run(args.features, args.task, args.output,
        distance=args.distance, jobs=args.jobs)

if __name__ == '__main__':
    main()
