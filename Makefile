PYTHON   = python3


build:
	$(PYTHON) setup.py build

test:
	$(PYTHON) setup.py test

sdist:
	$(PYTHON) setup.py sdist

clean:
	rm -f *~ archive/*~ tests/*~
	rm -rf build

distclean: clean
	rm -f MANIFEST
	rm -f archive/*.pyc tests/*.pyc
	rm -rf .cache
	rm -rf archive/__pycache__ tests/__pycache__
	rm -rf dist


.PHONY: build test sdist clean distclean
