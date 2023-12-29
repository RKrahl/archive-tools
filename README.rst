|gh-test| |pypi|

.. |gh-test| image:: https://img.shields.io/github/actions/workflow/status/RKrahl/archive-tools/run-tests.yaml?branch=develop
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

+ `setuptools`_

+ `PyYAML`_

+ `packaging`_

+ `lark`_

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

+ `git-props`_

  This package is used to extract some metadata such as the version
  number out of git, the version control system.  All releases embed
  that metadata in the distribution.  So this package is only needed
  to build out of the plain development source tree as cloned from
  GitHub, but not to build a release distribution.

+ `pytest`_ >= 3.0

  Only needed to run the test suite.

+ `distutils-pytest`_

  Only needed to run the test suite.

+ `pytest-dependency`_ >= 0.2

  Only needed to run the test suite.


Copyright and License
---------------------

Copyright 2019–2023 Rolf Krahl

Licensed under the `Apache License`_, Version 2.0 (the "License"); you
may not use this package except in compliance with the License.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied.  See the License for the specific language governing
permissions and limitations under the License.


.. _setuptools: https://github.com/pypa/setuptools/
.. _PyPI site: https://pypi.org/project/archive-tools/
.. _PyYAML: https://pypi.org/project/PyYAML/
.. _packaging: https://github.com/pypa/packaging/
.. _lark: https://github.com/lark-parser/lark
.. _imapclient: https://github.com/mjs/imapclient/
.. _python-dateutil: https://dateutil.readthedocs.io/en/stable/
.. _git-props: https://github.com/RKrahl/git-props
.. _pytest: https://pytest.org/
.. _distutils-pytest: https://github.com/RKrahl/distutils-pytest
.. _pytest-dependency: https://pypi.python.org/pypi/pytest_dependency/
.. _Apache License: https://www.apache.org/licenses/LICENSE-2.0
