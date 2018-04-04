.PHONY: test build install clean
	
test:
	python setup.py test

build:
	python setup.py build

install:
	python setup.py install

clean:
	find . -name '*.pyc' -delete
	find . -name '*.so' -delete
