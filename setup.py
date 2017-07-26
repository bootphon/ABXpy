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
        import subprocess
        try:
            import pytest
        except ImportError:
            raise ImportError(
                'You need to have pytest to run the tests,'
                ' try installing it (pip install pytest)')
        errno = subprocess.call(['pytest', '-s', 'ABXpy/test'])
        raise SystemExit(errno)


extension = Extension(
    'ABXpy.distances.metrics.dtw',
    sources=[os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'ABXpy', 'distances', 'metrics', 'install', 'dtw.pyx')],
    extra_compile_args=['-O3'],
    include_dirs=[numpy.get_include()])


setup(
    name='ABXpy',
    version='0.1.0',
    author='Thomas Schatz',
    description='ABX discrimination task',
    long_description=open('README.rst').read(),
    url='https://github.com/bootphon/ABXpy',
    license='license/LICENSE.txt',

    packages=[
        'ABXpy',
        'ABXpy.test',
        'ABXpy.database',
        'ABXpy.dbfun',
        'ABXpy.distances',
        'ABXpy.h5tools',
        'ABXpy.misc',
        'ABXpy.sampling',
        'ABXpy.sideop',
        'ABXpy.distances.metrics'],

    # FIXME add cython as well?
    install_requires=[
        "python >= 2.7",
        "h5py >= 2.2.1",
        "numpy >= 1.8.0",
        "pandas >= 0.13.1",
        "scipy >= 0.13.0",
        "tables",
    ],

    ext_modules=cythonize(extension),
    cmdclass={'test': PyTest},

    entry_points={'console_scripts': [
        'abx-task = ABXpy.task:main',
        'abx-distance = ABXpy.distance:main',
        'abx-analyze = ABXpy.analyze:main',
        'abx-score = ABXpy.score:main',
    ]}
)
