testing:
	make install
	py.test -s test

install:
	python ABXpy/distances/metrics/install/install_dtw.py

clean:
	find . -name '*.pyc' -delete
	find . -name '*.so' -delete