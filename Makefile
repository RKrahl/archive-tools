PYTHON = python3


build:
	$(PYTHON) setup.py build

test:
	$(PYTHON) setup.py test

sdist:
	$(PYTHON) setup.py sdist

clean:
	rm -rf build
	rm -rf __pycache__

distclean: clean
	rm -f MANIFEST _meta.py
	rm -rf dist
	rm -rf tests/.pytest_cache

meta:
	$(PYTHON) setup.py meta


.PHONY: build test sdist clean distclean meta
