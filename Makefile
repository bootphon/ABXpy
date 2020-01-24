# simple makefile to simplify repetitive build env management tasks under posix

PYTHON ?= python

.PHONY: build install develop doc test clean

build:
	$(PYTHON) setup.py build

install: build
	$(PYTHON) setup.py install

develop: build
	$(PYTHON) setup.py develop

doc: build
	$(PYTHON) setup.py build_sphinx

test: build
	$(PYTHON) setup.py test

clean:
	$(PYTHON) setup.py clean
	find . -name '*.pyc' -delete
	find . -name '*.so' -delete
	find . -name __pycache__ -exec rm -rf {} +
	rm -rf .eggs *.egg-info
	rm -rf ABXpy/distances/metrics/dtw/*.c
	rm -rf build dist htmlcov .coverage*
