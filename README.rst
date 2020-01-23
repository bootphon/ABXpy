.. image:: https://travis-ci.org/bootphon/ABXpy.svg?branch=master
    :target: https://travis-ci.org/bootphon/ABXpy
.. image:: https://codecov.io/gh/bootphon/ABXpy/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/bootphon/ABXpy
.. image:: https://anaconda.org/coml/abx/badges/version.svg
    :target: https://anaconda.org/coml/abx
.. image:: https://zenodo.org/badge/23788452.svg
    :target: https://zenodo.org/badge/latestdoi/23788452

ABX discrimination test
=======================

ABX discrimination is a term that is used for three stimuli presented
on an ABX trial. The third is the focus. The first two stimuli (A
and B) are standard, S1 and S2 in a randomly chosen order, and the
subjects' task is to choose which of the two is matched by the final
stimulus (X). (Glottopedia)

This package contains the operations necessary to initialize,
calculate and analyse the results of an ABX discrimination task.

Check out the full documentation at https://coml.lscp.ens.fr/docs/abx.

Organisation
------------

It is composed of 3 main modules and other submodules.

- `task module
  <https://coml.lscp.ens.fr/abx/ABXpy.html#task-module>`_ is
  used for creating a new task and preprocessing.

- `distances package
  <https://coml.lscp.ens.fr/abx/ABXpy.distances.html>`_ is
  used for calculating the distances necessary for the score
  calculation.

- `score module
  <https://coml.lscp.ens.fr/abx/ABXpy.html#score-module>`_
  is used for computing the score of a task.

- `analyze module
  <https://coml.lscp.ens.fr/abx/ABXpy.html#analyze-module>`_
  is used for analysing the results.

The features can be calculated in numpy via external tools, and made
compatible with this package with the `h5features module
<http://h5features.readthedocs.org/en/latest/h5features.html>`_, or
directly calculated with one of our tools like `shennong
<http://h5features.readthedocs.org/en/latest/h5features.html#module-npz2h5features>`_.

The pipeline
------------

+-------------------+----------+-----------------+
| In                | Module   | Out             |
+===================+==========+=================+
| - data.item       | task     | - data.abx      |
| - parameters      |          |                 |
+-------------------+----------+-----------------+
| - data.abx        | distance | - data.distance |
| - data.features   |          |                 |
| - distance        |          |                 |
+-------------------+----------+-----------------+
| - data.abx        | score    | - data.score    |
| - data.distance   |          |                 |
+-------------------+----------+-----------------+
| - data.abx        | analyse  | - data.csv      |
| - data.score      |          |                 |
+-------------------+----------+-----------------+

See `Files Format
<https://coml.lscp.ens.fr/abx/FilesFormat.html>`_ for a
description of the files used as input and output.

The task
--------

According to what you want to study, it is important to characterise
the ABX triplets. You can characterise your task along 3 axes: on,
across and by a certain label.

An example of ABX triplet:

+------+------+------+
|  A   |  B   |  X   |
+======+======+======+
| on_1 | on_2 | on_1 |
+------+------+------+
| ac_1 | ac_1 | ac_2 |
+------+------+------+
| by   | by   | by   |
+------+------+------+

A and X share the same 'on' attribute; A and B share the same 'across'
attribute; A,B and X share the same 'by' attribute.

Example of use
--------------

See ``examples/complete_run.sh`` for a command line run and
``examples/complete_run.py`` for a Python utilisation.


Installation
------------

The recommended installation on linux and macos is using `conda
<https://docs.conda.io/en/latest/miniconda.html>`_::

  conda install -c coml abx

Alternatively you may want to install it from sources. First clone
this repository and go to its root directory. Then ::

    conda env create -n abx -f environment.yml
    source activate abx
    make install
    make test


Build the documentation
-----------------------

To build the documentation in the folder ``ABXpy/build/doc/html``,
simply have a::

    make doc


Citation
--------

If you use this software in your research, please cite:

  `ABX-discriminability measures and applications
  <https://hal.archives-ouvertes.fr/tel-01407461/file/Schatz2016.pdf>`_,
  Schatz T., Université Paris 6 (UPMC), 2016.
