"""This package contains the operations necessary to initialize, calculate and
analyse the results of an ABX discrimination task.

Organisation
------------
It is composed of 3 main modules and other submodules.

- `task module`_ is used for creating a new task and preprocessing.
- `score module`_ is used for computing the score of a task.
- `analyze module`_ is used for analysing the results.

The pipeline
------------
#TODO graphic description of the pipeline
"""
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 18 22:31:59 2013

@author: thomas

This file only serves to signal that ABXpy is a Python package.
"""

#FIXME at least h5tools, dbfun, sampling and distances should be put in independent repositories
#FIXME should take care of ABX specifics import here once and for all, so as to not have to do them again in all modules? using relative imports for security and python3 compatibility? 
# this should allow not having __init__.py in every subfolder