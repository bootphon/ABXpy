from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
import os
import numpy


path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                    'ABXpy/distances/metrics/install')
extension = Extension("ABXpy.distances.metrics.dtw",
                      [os.path.join(path, "dtw.pyx")],
                      extra_compile_args=["-O3"],
                      include_dirs=[numpy.get_include()])

setup(
    name='ABXpy',
    version='0.1.0',
    author='Thomas Schatz',
    packages=['ABXpy', 'ABXpy.test', 'ABXpy.database', 'ABXpy.dbfun',
              'ABXpy.distances', 'ABXpy.h5tools', 'ABXpy.misc',
              'ABXpy.sampling', 'ABXpy.sideop', 'ABXpy.distances.metrics'],
    scripts=['bin/ABXrun.py'],
    # url='http://pypi.python.org/pypi/ABXpy/',
    license='license/LICENSE.txt',
    description='ABX discrimination task.',
    long_description=open('README.rst').read(),
    ext_modules=cythonize(extension),
    install_requires=[
        "python >= 2.7",
        "h5py >= 2.3.0",
        "numpy >= 1.8.0",
        "pandas >= 0.13.1",
        "scipy >= 0.14.0"
    ],
)
