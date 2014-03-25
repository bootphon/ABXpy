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
    bin_folder = os.path.dirname(script_folder)
    tmp_folder = os.path.join(script_folder, 'tmp')
    install_script = os.path.join(script_folder, 'compile_dtw.py')
    # create .c and .so
    subprocess.call("%s %s build_ext --build-lib %s --build-temp %s" % (python, install_script, bin_folder, tmp_folder), shell=True)
    # clean-up tmp
    subprocess.call("rm -Rf %s" % tmp_folder, shell=True)


if __name__ == '__main__': # detects whether the script was called from command-line
    
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('python', nargs='?', default=None, help='optional: python executable to be used')
    args = parser.parse_args()  
    
    if args.python is None:
        args.python = 'python'
        
    install_dtw(args.python)
        
    