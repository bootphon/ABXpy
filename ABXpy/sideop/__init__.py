# -*- coding: utf-8 -*-
"""
Created on Sun Aug 18 22:31:59 2013

:author: thomas

This module contains the filter and regressor managers used by task to apply
the filters and regressors. Both those classes use a side operation manager
that implement the generic functions. This allow to apply the filters and
regressors as early as possible during the triplet generation to optimise the
performances.
"""
