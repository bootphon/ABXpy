=========
ChangeLog
=========

ABXpy-0.4.3
===========

* no more compatibility with **python2** (and removed dependency to future/past).

* new feature: add *editdistance* as available distance.

* bugfix with python-3.8 and *ast.Module*.

* fixed a lot of deprecation warnings.

* documentation moved to https://coml.lscp.ens.fr/docs/abx


ABXpy-0.4.2
===========

* compatibility with **python3**

* releases are now deployed on `conda
  <https://anaconda.org/coml/abx>`_ for linux and macos.

* documentation is hosted on https://coml.lscp.ens.fr/abx

* bugfixes:

  * bugfix in the Kullback Leibler divergence metric with numpy array shape

  * bugfix: cosine.py returned shape (1,1,1,1) instead of (1,1) when
    metric(x,y) is shape (1,1)


ABXpy-0.4.1
===========

No ChangeLog beyond this release.
