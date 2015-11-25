#!/usr/bin/env python
"""Provides a command-line API to ABX.verify"""

import argparse

from ABXpy.verify import check

def parse_args():
    parser = argparse.ArgumentParser(
        prog='collapse_results.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Collapse results of ABX on by conditions.',
        epilog="""Example usage:

$ ./verify.py my_data.item my_features.h5f

verify the consistency between the item file and the features file""")
    parser.add_argument('item', metavar='ITEM_FILE',
                        help='database description file in .item format')
    parser.add_argument('features', metavar='FEATURES_FILE',
                        help='features file in h5features format')
    return parser.parse_args()


def main():
    args = parse_args()
    check(args.item, args.features)


if __name__ == '__main__':
    main()
