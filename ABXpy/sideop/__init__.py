"""This module contains the filter and regressor managers used by
task to apply the filters and regressors. Both those classes use a
side operation manager that implement the generic functions. This
allow to apply the filters and regressors as early as possible during
the triplet generation to optimise the performances.

"""
