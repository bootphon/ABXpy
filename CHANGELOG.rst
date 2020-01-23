=========
ChangeLog
=========

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
