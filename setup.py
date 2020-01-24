import setuptools
import setuptools.command.build_ext
import ABXpy


class build_ext(setuptools.command.build_ext.build_ext):
    def finalize_options(self):
        setuptools.command.build_ext.build_ext.finalize_options(self)
        # Prevent numpy from thinking it is still in its setup process:
        __builtins__.__NUMPY_SETUP__ = False
        import numpy
        self.include_dirs.append(numpy.get_include())


setuptools.setup(
    name='ABXpy',
    version=ABXpy.version,
    author='Thomas Schatz',
    description='ABX discrimination task',
    long_description=open('README.rst').read(),
    url='https://github.com/bootphon/ABXpy',
    license='LICENSE.txt',

    packages=setuptools.find_packages(exclude='test'),

    # needed for cython/setuptools, see
    # http://docs.cython.org/en/latest/src/quickstart/build.html
    zip_safe=False,

    setup_requires=[
        'editdistance',
        'cython',
        'setuptools>=18.0',
        'numpy>=1.9.0',
        'pytest-runner'
    ],

    install_requires=[
        'h5py >= 2.2.1',
        'numpy >= 1.8.0',
        'pandas >= 0.13.1',
        'scipy >= 0.13.0',
        'tables',
    ],

    tests_require=[
        'h5features',
        'pytest>=2.6',
        'pytest-cov'
    ],

    ext_modules=[setuptools.Extension(
        'ABXpy.distances.metrics.dtw',
        sources=['ABXpy/distances/metrics/dtw/dtw.pyx'],
        extra_compile_args=['-O3'])],

    cmdclass={'build_ext': build_ext},

    entry_points={'console_scripts': [
        'abx-task = ABXpy.task:main',
        'abx-distance = ABXpy.distance:main',
        'abx-analyze = ABXpy.analyze:main',
        'abx-score = ABXpy.score:main',
    ]}
)
