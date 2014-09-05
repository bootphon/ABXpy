# -*- coding: utf-8 -*-
"""
Created on Fri May  2 09:33:20 2014

@author: Thomas Schatz
"""
import h5features
import os
import numpy as np
import glob


def npz_to_h5features(path, files, h5_filename, h5_groupname, batch_size=500):
        features = []
        times = []
        internal_files = []
        i = 0
        for f in files:
            if i == batch_size:
                h5features.write(h5_filename, h5_groupname, internal_files,
                                 times, features)
                features = []
                times = []
                internal_files = []
                i = 0
            i = i+1
            data = np.load(os.path.join(path, f))
            features.append(data['features'])
            times.append(data['time'])
            internal_files.append(os.path.splitext(f)[0])
        if features:
            h5features.write(h5_filename, h5_groupname, internal_files, times,
                             features)


def convert(npz_folder, h5_filename='./features.features'):
    files = [os.path.basename(f) for f in glob.glob(npz_folder + '*.npz')]
    npz_to_h5features(npz_folder, files, h5_filename, '/features/')

if __name__ == '__main__':  # detects if the script was called from commandline

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('npz_folder',
                        help='folder containing the npz files to be converted')
    parser.add_argument('h5_filename',
                        help='desired path for the h5features file')
    args = parser.parse_args()
    convert(args.npz_folder, args.h5_filename)
