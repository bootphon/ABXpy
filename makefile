test:
	make install
	py.test -s ABXpy/test

install:
	python ABXpy/distances/metrics/install/install_dtw.py
	python setup.py build
	python setup.py install

clean:
	find . -name '*.pyc' -delete
	find . -name '*.so' -delete
