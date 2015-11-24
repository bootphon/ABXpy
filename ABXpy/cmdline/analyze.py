#!/usr/bin/env python
"""Provides a command-line API to ABX.analyze"""

import argparse
import os

from ABXpy.analyze import analyze

def parse_args():
    parser = argparse.ArgumentParser(
        prog='analyze.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Collapse results of ABX score on type of ABX triplet.',
        epilog="""Example usage:

$ ./analyze.py abx.score abx.task abx.csv

compute the average the scores in abx.score by type of ABX triplet
and output the results in tab separated csv format.""")

    parser.add_argument('scorefile', metavar='SCORE',
                        help='score file in hdf5 format')
    parser.add_argument('taskfile', metavar='TASK',
                        help='task file in hdf5 format')
    parser.add_argument('output', metavar='OUTPUT',
                        help='output file in csv format')
    return vars(parser.parse_args())


if __name__ == '__main__':
    args = parse_args()

    score_file = args['scorefile']
    if not os.path.exists(score_file):
        print('No such file: {}'.format(score_file))
        exit()

    task_file = args['taskfile']
    if not os.path.exists(task_file):
        print('No such file: {}'.format(task_file))
        exit()

    result_file = args['output']
    if os.path.exists(result_file):
        print("Warning: overwriting analyze file {}".format(result_file))
        os.remove(result_file)

    analyze(task_file, score_file, result_file)
