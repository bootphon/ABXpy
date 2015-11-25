#!/usr/bin/env python
"""This test script contains tests for the basic parameters of score.py"""

import json
import os

import ABXpy.task
import ABXpy.distances.distances as distances
from ABXpy.distances.example_distances import dtw_cosine
import ABXpy.score as score
import ABXpy.analyze as analyze


def get_name(filename):
    return os.path.splitext(os.path.basename(filename))[0]


def get_arg(key, args):
    if key in args:
        return args[key]
    else:
        return None

def test_analyze(itemfile, featurefile, args, taskfile=None, distance=None,
                 distancefile=None, scorefile=None, analyzefile=None,
                 filename=None):

    on = get_arg('on', args)
    assert on, ("The 'on' argument was not found, this argument is mandatory"
                "for the task")
    across = get_arg('across')
    by = get_arg('by')
    filters = get_arg('filters')
    reg = get_arg('reg')

    if not filename:
        filename = '_'.join(filter(None, [get_name(itemfile),
                                          get_name(featurefile),
                                          str(on),
                                          str(across),
                                          str(by)]))
    if not distancefile:
        distancefile = filename + '.distance'
    if not scorefile:
        scorefile = filename + '.score'
    if not analyzefile:
        analyzefile = filename + '.csv'

    task = ABXpy.task.Task(itemfile, on, across, by, filters, reg,
                           features=featurefile)
    task.generate_triplets()

    if not distance:
        distance = dtw_cosine
    distances.compute_distances(featurefile, '/features/', taskfile,
                                distancefile, distance)
    score.score(taskfile, distancefile, scorefile)
    analyze.analyze(scorefile, taskfile, analyzefile)


def parse_args():
    parser = argparse.ArgumentParser(
        prog='ABXrun.py',
        # formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Run the complete ABXpy pipeline.',
        epilog="""Example usage:

$ python ABXrun data.item data.feature data.conf
""")
    parser.add_argument(
        'itemfile', metavar='itemfile',
        help='Input item file in item format, e.g. data.item')
    parser.add_argument(
        'featurefile', metavar='featurefile',
        help='Input feature file in h5features format, e.g. data.features')
    parser.add_argument(
        'config', metavar='configfile',
        help='Input config file in json format, e.g. data.conf.\n'
             'This file should at least contain the task parameters. '
             'You can also include the filenames you want to use and the saga'
             ' parameters.')
    parser.add_argument(
        '--taskfile', metavar='taskfile',
        required=False,
        help='Output task file where the task information will be stored, e.g.'
             ' data.abx.')
    parser.add_argument(
        '--distancefile', metavar='distancefile',
        required=False,
        help='Output distance file where the distances between pairs will be '
             'stored, e.g. data.distance')
    parser.add_argument(
        '--analyzefile', metavar='analyzefile',
        required=False,
        help='Output analyze file where the collapsed results will be stored, '
             'e.g. data.csv')
    parser.add_argument(
        '--scorefile', metavar='scorefile',
        required=False,
        help='Output score file where the score of the triplets will be stored'
             ', e.g. data.score')
    parser.add_argument(
        '--distance', metavar='distance',
        required=False,
        help='Callable distance function to be used for distance calculation,'
             ' by default the dynamic time warping cosine distance will be '
             'used')
    parser.add_argument(
        '--name', metavar='filename',
        required=False,
        help='If you specify a filename, all the files generated will have '
             'the same basename and a standard extension. For instance, the '
             'task file will be named filename.abx')
    return vars(parser.parse_args())


if __name__ == '__main__':

    import argparse

    args = parse_args()

    # mandatory args
    itemfile = args['itemfile']
    assert os.path.exists(itemfile)
    featurefile = args('featurefile')
    assert os.path.exists(featurefile)
    configfile = args('configfile')
    assert os.path.exists(configfile)
    try:
        with open(configfile, 'r') as fid:
            config = json.load(fid)
    except IOError:
        print('No such file: ', configfile)
        exit()
    assert get_arg('on', config)

    # optional args
    taskfile = get_arg('taskfile', args)
    if not taskfile:
        taskfile = get_arg('taskfile', config)
    distancefile = get_arg('distancefile', args)
    if not distancefile:
        distancefile = get_arg('distancefile', config)
    scorefile = get_arg('scorefile', args)
    if not scorefile:
        scorefile = get_arg('scorefile', config)
    analyzefile = get_arg('analyzefile', args)
    if not analyzefile:
        analyzefile = get_arg('analyzefile', config)
    distance = get_arg('distance', args)
    if not distance:
        distance = get_arg('distance', config)
    filename = get_arg('filename', args)
    if not filename:
        filename = get_arg('filename', config)

    test_analyze(itemfile, featurefile, config, taskfile, distance,
                 distancefile, scorefile, analyzefile,
                 filename)
