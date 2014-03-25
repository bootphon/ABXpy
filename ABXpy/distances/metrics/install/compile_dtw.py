# -*- coding: utf-8 -*-
"""
Created on Mon Oct 28 11:30:48 2013

@author: Thomas Schatz
"""

from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
import numpy, os
path = os.path.dirname(os.path.realpath(__file__))

extension = Extension("dtw", [os.path.join(path, "dtw.pyx")], extra_compile_args=["-O3"], include_dirs=[numpy.get_include()])

setup(name = "DTW implementation in cython", ext_modules = cythonize(extension))