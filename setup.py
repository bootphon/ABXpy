try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from distutils.core import Command
from distutils.extension import Extension
from Cython.Build import cythonize
import os
import numpy


class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys,subprocess
        try:
            import pytest
        except ImportError:
            raise(ImportError, 'You need to have pytest to run the tests,'
                  ' try installing it (pip install pytest)')
        errno = subprocess.call(['py.test', '-s', 'test'])
        raise SystemExit(errno)


path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                    'ABXpy/distances/metrics/install')
lib = os.path.dirname(path)
extension = Extension("ABXpy.distances.metrics.dtw",
                      sources=[os.path.join(path, "dtw.pyx")],
                      extra_compile_args=["-O3"],
                      include_dirs=[numpy.get_include()])

setup(
    name='ABXpy',
    version='0.1.0',
    author='Thomas Schatz',
    packages=['ABXpy', 'ABXpy.cmdline', 'ABXpy.database', 'ABXpy.dbfun',
              'ABXpy.distances', 'ABXpy.h5tools', 'ABXpy.misc',
              'ABXpy.sampling', 'ABXpy.sideop', 'ABXpy.distances.metrics'],
    # url='http://pypi.python.org/pypi/ABXpy/',
    license='LICENSE.txt',
    description='ABX discrimination task.',
    long_description=open('README.rst').read(),
    ext_modules=cythonize(extension),
    install_requires=[
        #"python >= 3.4",
        "h5py >= 2.2.1",
        "numpy >= 1.8.0",
        "pandas >= 0.13.1",
        "scipy >= 0.13.0",
        "tinytree >= 0.2.1"
    ],
    cmdclass = {'test': PyTest},
)
