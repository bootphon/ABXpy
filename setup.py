from setuptools import setup
from distutils.core import Command
from distutils.extension import Extension
from setuptools.command.build_ext import build_ext as _build_ext


import pkg_resources
import os


class build_ext(_build_ext):
    def finalize_options(self):
        _build_ext.finalize_options(self)
        # Prevent numpy from thinking it is still in its setup process:
        __builtins__.__NUMPY_SETUP__ = False
        import numpy
        self.include_dirs.append(numpy.get_include())


extension = Extension(
    'ABXpy.distances.metrics.dtw',
    sources=[os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'ABXpy', 'distances', 'metrics', 'dtw', 'dtw.pyx')],
    extra_compile_args=['-O3'],
)


setup(
    name='ABXpy',
    version='0.1.1',
    author='Thomas Schatz',
    description='ABX discrimination task',
    long_description=open('README.rst').read(),
    url='https://github.com/bootphon/ABXpy',
    license='license/LICENSE.txt',

    packages=[
        'ABXpy',
        'ABXpy.database',
        'ABXpy.dbfun',
        'ABXpy.distances',
        'ABXpy.h5tools',
        'ABXpy.misc',
        'ABXpy.sampling',
        'ABXpy.sideop',
        'ABXpy.distances.metrics',
    ],

    setup_requires=[
        # Setuptools 18.0 properly handles Cython extensions.
        'setuptools>=18.0',
        'numpy>=1.9.0',
        "pytest-runner",
    ],

    install_requires=[
        "h5py >= 2.2.1",
        "numpy >= 1.8.0",
        "pandas >= 0.13.1",
        "scipy >= 0.13.0",
        "tables",
        "future",
    ],
    
    tests_require=[
        "h5features",
        "pytest>=2.6",
    ],

    ext_modules=[extension],

    cmdclass={'build_ext': build_ext},

    entry_points={'console_scripts': [
        'abx-task = ABXpy.task:main',
        'abx-distance = ABXpy.distance:main',
        'abx-analyze = ABXpy.analyze:main',
        'abx-score = ABXpy.score:main',
    ]}
)
