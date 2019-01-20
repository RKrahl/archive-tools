PYTHON   = python3


build:
	$(PYTHON) setup.py build

test:
	$(PYTHON) setup.py test

sdist:
	$(PYTHON) setup.py sdist

clean:
	rm -f *~ archive/*~ scripts/*~ tests/*~
	rm -rf build

distclean: clean
	rm -f MANIFEST
	rm -f archive/*.pyc scripts/*.pyc tests/*.pyc
	rm -rf archive/__pycache__ scripts/__pycache__ tests/__pycache__
	rm -rf .cache
	rm -rf dist


.PHONY: build test sdist clean distclean
