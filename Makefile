PYTHON   = python3


build:
	$(PYTHON) setup.py build

test:
	$(PYTHON) setup.py test

sdist:
	$(PYTHON) setup.py sdist

doc-html: init_py
	$(MAKE) -C doc html

doc-pdf: init_py
	$(MAKE) -C doc latexpdf

clean:
	rm -f *~ archive/*~ scripts/*~ tests/*~
	rm -rf build

distclean: clean
	rm -f archive/*.pyc scripts/*.pyc tests/*.pyc
	rm -rf archive/__pycache__ scripts/__pycache__ tests/__pycache__
	rm -rf tests/.cache tests/.pytest_cache
	rm -f MANIFEST .version
	rm -f archive/__init__.py
	rm -rf dist
	$(MAKE) -C doc distclean

init_py:
	$(PYTHON) setup.py init_py


.PHONY: build test sdist doc-html doc-pdf clean distclean init_py
