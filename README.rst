Zerospeech2015 Challenge
========================

This repository contains the code necessary to replicate the track 1 evaluation of the Zerospeech2015 challenge.

The complete description of the challenge can be found `here <http://www.lscp.net/persons/dupoux/bootphon/zerospeech2014/website/>`_.


Installation:
-------------

.. code:: bash

	  python setup.py build && python setup.py install

Preparation (only once):
------------------------

.. code:: bash
	  
	  python bin/prepare.py

.. note:: This script can take a while, you can select which corpus to prepare with the '-c' option.
	  
	  E.g.: python bin/prepare.py -c sample

Run:
----

.. code:: bash

	  python bin/{sample, english, xitsonga}_eval1.py FEATURES_FOLDER OUTPUT_FOLDER

Scripts:
~~~~~~~~

There are 3 scripts, one for each dataset: sample, english and xitsonga.

Two examples of features are provided for the sample set: MFCC and HTKposteriors.


FEATURES_FOLDER:
~~~~~~~~~~~~~~~~

Our evaluation system requires that your unsupervised subword modeling system outputs a vector of feature values for each frame. For each utterance in the set (e.g. s2801a.wav), an ASCII features file with the same name (e.g. s2801a.fea) as the utterance should be generated with the following format:

::

     <time> <val1>    ... <valN>
     <time> <val1>    ... <valN>

example:

::

     0.0125 12.3 428.8 -92.3 0.021 43.23         
     0.0225 19.0 392.9 -43.1 10.29 40.02

.. note:: The time is in seconds. It corresponds to the center of the frame of each feature. In this example, there are frames every 10ms and the first frame spans a duration of 25ms starting at the beginning of the file, hence, the first frame is centered at .0125 seconds and the second 10ms later. It is not required that the frames be regularly spaced.

OUTPUT_FOLDER:
~~~~~~~~~~~~~~

Output folder were the intermediate files and the results will be stored.

Optionnal arguments:
~~~~~~~~~~~~~~~~~~~~

* -j N_CORES: number of cpus to use.

* --csv: store the pre-average results in csv format. Useful to compute statistics on the results or to get a better understanding.

* -kl: Using DTW Kullback Leiber divergence (instead of DTW cosine distance by default).

* -d DISTANCE: Using user defined distance (for an example of code, see resources/distance.py for some examples). 
  DISTANCE argument should be 'distance_module.distance_function'. E.g.: to use KL-divergence, -d resources/distance.kl_divergence

Examples:
~~~~~~~~~

.. code:: bash

	  python bin/sample_eval1.py MFCC MFCCscore -j 4
	  python bin/sample_eval1.py HTKposteriors HTKscore -kl -j 4 --csv
	  python bin/sample_eval1.py HTKposteriors HTKscore -d resources/distance.kl_divergence -j 4 --csv


ABX discrimination test.
========================

ABX discrimination is a term that is used for three stimuli presented on an ABX trial. The third is the focus. The first two stimuli (A and B) are standard, S1 and S2 in a randomly chosen order, and the subjects' task is to choose which of the two is matched by the final stimulus (X). (Glottopedia)

This package contains the operations necessary to initialize, calculate and analyse the results of an ABX discrimination task.

Check out the full documentation at `read the docs <http://abxpy.readthedocs.org/en/latest/ABXpy.html>`_.

Organisation
------------
It is composed of 3 main modules and other submodules.

- `task module <http://abxpy.readthedocs.org/en/latest/ABXpy.html#task-module>`_ is used for creating a new task and preprocessing.
- `distances package <http://abxpy.readthedocs.rg/en/latest/ABXpy.distances.html>`_ is used for calculating the distances necessary for the score calculation.
- `score module <http://abxpy.readthedocs.org/en/latest/ABXpy.html#score-module>`_ is used for computing the score of a task.
- `analyze module <http://abxpy.readthedocs.org/en/latest/ABXpy.html#analyze-module>`_ is used for analysing the results.

The features can be calculated in numpy via external tools, and made compatible with this package with the `h5features module <http://h5features.readthedocs.org/en/latest/h5features.html>`_, or directly calculated with one of our tools like the `feature_extraction module <http://h5features.readthedocs.org/en/latest/h5features.html#module-npz2h5features>`_.

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

See `Files Format <http://abxpy.readthedocs.org/en/latest/FilesFormat.html>`_ for a description of the files used as input and output.

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

See examples/complete_run.sh for a command line run and examples/complete_run.py for a python utilisation.

Installation
------------

The module should work with the anaconda distribution of python. However, you may get some (unrelevant) warnings while running task.py.

	make
	make install

Run the tests
-------------

Note that you will need `h5features module <http://h5features.readthedocs.org/en/latest/h5features.html>`_ in your path for some tests to work.

    make test

Generate the documentation
---------------------------

Note that you will get warnings if you don't have the `h5features module <http://h5features.readthedocs.org/en/latest/h5features.html>`_ in your path.

    cd docs
    make html

(you can also generate the doc in several other formats, see the Makefile)


Citation
---------

If you use this software in your research, please cite: 
  ABX discriminability, Schatz T., Bach F. and Dupoux E., in preparation.

Travis status
-------------

This package is continuously integrated with Travis-CI:

.. image:: https://travis-ci.org/bootphon/ABXpy.svg?branch=master
    :target: https://travis-ci.org/bootphon/ABXpy
