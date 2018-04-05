.PHONY: test build install clean
	
test:
	python setup.py test

ftest: # fails on first error
	python setup.py test -a '-x'

build:
	python setup.py build

install:
	python setup.py install

clean:
	find . -name '*.pyc' -delete
	find . -name '*.so' -delete
	python setup.py clean --all
	rm -rf ABXpy/distances/metrics/dtw/*.c