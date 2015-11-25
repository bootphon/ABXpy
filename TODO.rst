=========
TODO list
=========

Scheduled (Mathieu)
===================

* Put all the front-end scripts in ABXpy/cmdline

  * make a wrapper on everything after task.
  * unified exceptions catching at top level, write proper error messages
  * unified logging facilities

* Isolate parallel machinery from the distances module.


Project wide TODOs
==================

* python3 compatibility

* clean up the misc subpackage

  * replace any2h5features by h5features.Converter, or delete it ?

* proper copyright in source

* integrate a generic collapse to ABX-score and output in R and csv
  format **URGENT**

* more complete test suite

* more complete documentation


On task.py
==========

* Add metadata in the task file (author, data, path to original data, etc)

* get a memory and speed efficient mechanism for storing a task on
  disk and loading it back (pickling doesn't work well)

* filter out empty 'on-across-by' blocks and empty 'by' blocks as soon
  as possible (i.e. when computing stats)

* generate unique_pairs in separate file

* find a better scheme for naming 'by' datasets in HDF5 files (to
  remove the current warning)

* efficiently dealing with case where there is no across

* syntax to specify names for side-ops when computing them on the fly
  or at the very least number of output (default is one)

* implementing file locking, md5 hash and path for integrity checks
  and logging warnings using the standard logging library of python +
  a verbose stuff

* putting metadata in h5files + pretty print it

* dataset size for task file seems too big when filtering so as to get
  only 3 different talkers ???

* allow specifying regressors and filters from within python using
  something like (which should be integrated with the existing dbfun
  stuff):

  .. code-block:: python

     class ABX_context(object):
        def __init__(self, db):
            init fields with None
            context = ABX_context(db_file)

        def new_filter(context):
            return [True for e in context.talker_A]

* allow other ways of providing the hierarchical db (directly in
  pandas format, etc.)

* replace verbose with the standard logging

* taking by datasets as the basic unit was a mistake, because
  cases where there many small by datasets happen. Find a way to group
  them when needed both in the computations and in the h5 files

* allow by sampling customization depending on the analyzes to
  be carried out

* Add a mechanism to allow the specification of a random seed in a way
  that would produce reliably the same triplets on different machines
  (means cross-platform random number generator + having its state so
  as to be sure that no other random number generation calls to it are
  altering the sequence)

* multicore for ABX-task (low priority)


On database.py
==============

* Why pandas for loading ? Speed ?

* Make database a class ?

* Remove the second # from database.item::

   #source onset   offset #label 1 label 2 label 3


On distance.py
==============

* correct the multicore bug **DONE?**

* Merge main() functions in distance and distances/distances

* Write distances.Features_Accessor.split_feature_file()

* Enforce single process usage when using python compiled with OMP
  enabled

* Detect when multiprocessed jobs crashed

* Write distances in a separate file. DONE ?

* Race condition in parallel computation -> 10 seconds wait to remove.

  
On score.py
===========

* Include distance computation in that module
