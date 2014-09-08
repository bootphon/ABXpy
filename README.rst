ABX discrimination test.
========================

ABX discrimination is a term that is used for three stimuli presented on an ABX trial. The third is the focus. The first two stimuli (A and B) are standard, S1 and S2 in a randomly chosen order, and the subjects' task is to choose which of the two is matched by the final stimulus (X). (Glottopedia)

This package contains the operations necessary to initialize, calculate and analyse the results of an ABX discrimination task.

Organisation
------------
It is composed of 3 main modules and other submodules.

- `task module <404>`_ is used for creating a new task and preprocessing.
- `distance package <404>`_ is used for calculating the\
    distances necessary for the score calculation.
- `score module <404>`_ is used for computing the score of a task.
- `analyze module <404>`_ is used for analysing the results.

The features can be calculated in numpy via external tools, and made compatible with this package with the `h5features module <404>`_, or directly calculated with one of our tools like the `feature_extraction module <404`_.

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

See `Files Format <404>`_ for a description of the files used as
input and output.

The task
--------

According to what you want to study, it is important to characterise the ABX triplets. You can characterise your task along 3 axes: on, across and by a certain label.

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

A and X share the same 'on' attribute; A and B share the same 'across' attribute; A,B and X share the same 'by' attribute.

Example of use
--------------
	TODO

Installation
------------

    The module should work with the anaconda distribution of python. However, you may get some (unrelevant) warnings while running task.py.

	make
	make install

Run the tests
-------------

    Note that you will need `h5features module <404>`_ in your path for some tests to work.

    make test

Generate the documentation:
---------------------------

    Note that you will get warnings if you don't have the `h5features module <404>`_ in your path.

    cd docs
    make html
    (you can also generate the doc in several thoer formats, see the Makefile)

