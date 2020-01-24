"""ABX discrimination test in Python

ABX discrimination is a term that is used for three stimuli presented on an
ABX trial. The third is the focus. The first two stimuli (A and B) are
standard, S1 and S2 in a randomly chosen order, and the subjects' task is to
choose which of the two is matched by the final stimulus (X). (Glottopedia)

This package contains the operations necessary to initialize, calculate and
analyse the results of an ABX discrimination task.

Organisation
------------

It is composed of 3 main modules and other submodules.

- `task module`_ is used for creating a new task and preprocessing.

- `distance package <ABXpy.distances.html>`_ is used for calculating the
  distances necessary for the score calculation.

- `score module`_ is used for computing the score of a task.

- `analyze module`_ is used for analysing the results.

The features can be calculated in numpy via external tools, and made
compatible with this package with the `npz2h5features
<http://h5features.readthedocs.org/en/latest/h5features.html#module-npz2h5features>`_
function.

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

See `Files Format <FilesFormat.html>`_ for a description of the files used as
input and output.

"""

version = "0.4.3"
