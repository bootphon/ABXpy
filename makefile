.PHONY: test build install clean
	
test:
	python setup.py test

ftest: # fails on first error
	python setup.py test -a '-sx'

build:
	python setup.py build

install:
	python setup.py install

clean:
	find . -name '*.pyc' -delete
	find . -name '*.so' -delete
	python setup.py clean --all
	rm -rf ABXpy/distances/metrics/dtw/*.c

conda:
	rm -rf conda_build
	conda build --output-folder conda_build -n .
	#conda convert --platform all outputdir/linux-64/*.tar.bz2 -o conda_build/
	anaconda upload --force -u coml conda_build/*/*.tar.bz2
