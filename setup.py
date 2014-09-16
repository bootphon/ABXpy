from distutils.core import setup


setup(
    name='ABXpy',
    version='0.1.0',
    author='Thomas Schatz',
    packages=['ABXpy', 'ABXpy.test', 'ABXpy.database', 'ABXpy.dbfun',
              'ABXpy.distances', 'ABXpy.h5tools', 'ABXpy.misc',
              'ABXpy.sampling', 'ABXpy.sideop', 'ABXpy.distances.metrics',
              'ABXpy.distances.metrics.dtw'],
    scripts=['bin/ABXrun.py'],
    # url='http://pypi.python.org/pypi/ABXpy/',
    license='license/LICENSE.txt',
    description='ABX discrimination task.',
    long_description=open('README.rst').read(),
    install_requires=[
        "python >= 2.7",
        "h5py >= 2.3.0",
        "numpy >= 1.8.0",
        "pandas >= 0.13.1",
        "scipy >= 0.14.0"
    ],
)
