# simple makefile to simplify repetitive build env management tasks under posix

PYTHON ?= python
PYTEST ?= pytest

.PHONY: build install develop doc test xtest clean

build:
	$(PYTHON) setup.py build

install: build
	$(PYTHON) setup.py install

develop: build
	$(PYTHON) setup.py develop

doc: build
	$(PYTHON) setup.py build_sphinx

test: build
	$(PYTEST)

xtest: build # fails on first error
	$(PYTEST) -x

clean:
	$(PYTHON) setup.py clean
	find . -name '*.pyc' -delete
	find . -name '*.so' -delete
	find . -name __pycache__ -exec rm -rf {} +
	rm -rf .eggs *.egg-info
	rm -rf ABXpy/distances/metrics/dtw/*.c
