|gh-test| |pypi|

.. |gh-test| image:: https://img.shields.io/github/workflow/status/RKrahl/archive-tools/Run%20Test
   :target: https://github.com/RKrahl/archive-tools/actions/workflows/run-tests.yaml
   :alt: GitHub Workflow Status
	 
.. |pypi| image:: https://img.shields.io/pypi/v/archive-tools
   :target: https://pypi.org/project/archive-tools/
   :alt: PyPI version

Tools for managing archives
===========================

This package provides tools for managing archives.  An archive in
terms of this package is a (compressed) tar archive file with some
embedded metadata on the included files.  This metadata include the
name, file stats, and checksums of the file.

The package provides a command line tool to enable the following
tasks:

+ Create an archive, takes a list of files to include in the archive
  as input.

+ Check the integrity and consistency of an archive.

+ List the contents of the archive.

+ Display details on a file in an archive.

+ Given a list of files as input, list those files that are either not
  in the archive or where the file in the archive differs.

All tasks providing information on an archive take this information
from the embedded metadata.  Retrieving this metadata does not require
reading through the compressed tar archive.


Download
--------

The latest release version is available on the
`Python Package Index (PyPI)`__.

.. __: `PyPI site`_


System requirements
-------------------

Python:

+ Python 3.6 or newer.

Required library packages:

+ `PyYAML`_

+ `lark-parser`_

  Required for the `backup-tool.py` script.

Optional library packages:

+ `imapclient`_

  Required for the `imap-to-archive.py` script.

+ `python-dateutil`_

  If the package is not available, some features will show slightly
  reduced functionality:

  - date strings will lack time zone indication.

  - the `--mtime` argument to `archive-tool.py find` recognizes a
    reduced set of date formats.

+ `setuptools_scm`_

  The version number is managed using this package.  All source
  distributions add a static text file with the version number and
  fall back using that if `setuptools_scm` is not available.  So this
  package is only needed to build out of the plain development source
  tree as cloned from GitHub.

+ `pytest`_ >= 3.0

  Only needed to run the test suite.

+ `distutils-pytest`_

  Only needed to run the test suite.

+ `pytest-dependency`_ >= 0.2

  Only needed to run the test suite.


Installation
------------

This package uses the distutils Python standard library package and
follows its conventions of packaging source distributions.  See the
documentation on `Installing Python Modules`_ for details or to
customize the install process.

1. Download the sources, unpack, and change into the source directory.

2. Build::

     $ python setup.py build

3. Test (optional)::

     $ python setup.py test

4. Install::

     $ python setup.py install

The last step might require admin privileges in order to write into
the site-packages directory of your Python installation.


Copyright and License
---------------------

Copyright 2019–2021 Rolf Krahl

Licensed under the `Apache License`_, Version 2.0 (the "License"); you
may not use this file except in compliance with the License.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied.  See the License for the specific language governing
permissions and limitations under the License.


.. _PyPI site: https://pypi.org/project/archive-tools/
.. _PyYAML: http://pyyaml.org/wiki/PyYAML
.. _lark-parser: https://github.com/lark-parser/lark
.. _imapclient: https://github.com/mjs/imapclient/
.. _python-dateutil: https://dateutil.readthedocs.io/en/stable/
.. _setuptools_scm: https://github.com/pypa/setuptools_scm/
.. _pytest: http://pytest.org/
.. _distutils-pytest: https://github.com/RKrahl/distutils-pytest
.. _pytest-dependency: https://pypi.python.org/pypi/pytest_dependency/
.. _Installing Python Modules: https://docs.python.org/3.7/install/
.. _Apache License: https://www.apache.org/licenses/LICENSE-2.0
