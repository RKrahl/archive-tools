PYTHON = python3
BUILDLIB = $(CURDIR)/build/lib


build:
	$(PYTHON) setup.py build

test:
	$(PYTHON) setup.py test

sdist:
	$(PYTHON) setup.py sdist

doc-html: build
	$(MAKE) -C doc html PYTHONPATH=$(BUILDLIB)

doc-pdf: build
	$(MAKE) -C doc latexpdf PYTHONPATH=$(BUILDLIB)

clean:
	rm -f *~ archive/*~ scripts/*~ tests/*~
	rm -rf build

distclean: clean
	rm -rf archive/__pycache__ scripts/__pycache__ tests/__pycache__
	rm -rf tests/.cache tests/.pytest_cache
	rm -f MANIFEST .version
	rm -f archive/__init__.py
	rm -rf dist
	$(MAKE) -C doc distclean

init_py:
	$(PYTHON) setup.py init_py


.PHONY: build test sdist doc-html doc-pdf clean distclean init_py
