# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 14:05:07 2014

@author: Thomas Schatz

Generic script for compiling DTW with cython
"""


import os, subprocess

def install_dtw(python):
    # find script directory
    script_folder = os.path.dirname(os.path.realpath(__file__))
    bin_folder = os.path.join(os.path.dirname(script_folder), 'bin')
    tmp_folder = os.path.join(script_folder, 'tmp')
    # create .c and .so
    subprocess.call("%s compile_dtw.py build_ext --build-lib %s --build-temp %s" % (python, bin_folder, tmp_folder), shell=True)
    # clean-up tmp
    subprocess.call("rm -Rf %s" % tmp_folder, shell=True)


if __name__ == '__main__': # detects whether the script was called from command-line
    
    import argparse
    
    # using lists as default value in the parser might be dangerous ? probably not as long as it is not used more than once ?
    # parser (the usage string is specified explicitly because the default does not show that the mandatory arguments must come before the mandatory ones; otherwise parsing is not possible beacause optional arguments can have various numbers of inputs)
    parser = argparse.ArgumentParser()
    parser.add_argument('python', nargs='?', default=None, help='optional: python executable to be used')
    args = parser.parse_args()  
    
    if args.python is None:
        args.python = 'python'
        
    install_dtw(args.python)
        
    