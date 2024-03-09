.. include:: _meta.rst

Installation instructions
=========================

See :ref:`install-using-pip` for the short version of the install
instructions.


System requirements
-------------------

Python
......

+ Python 3.6 or newer.

Required library packages
.........................

The following packages are required to install and use python-icat.
They will automatically be installed as dependencies if you install
using pip.

+ `setuptools`_

+ `packaging`_

+ `PyYAML`_ >= 5.1

+ `lark`_

  Required for the :ref:`backup-tool` script.  Not needed for the
  :ref:`archive-tools core API <modref-core>` or the
  :ref:`archive-tool` script,

Optional library packages
.........................

These packages are only needed to use certain extra features.  They
are not required to install archive-tools and use its core features:

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


Installation
------------

.. _install-using-pip:

Installation using pip
......................

You can install archive-tools from the
`Python Package Index (PyPI) <PyPI site_>`_ using pip::

  $ pip install archive-tools

Note that while installing from PyPI is convenient, there is no way to
verify the integrity of the source distribution, which may be
considered a security risk.

Installation from the source distribution
.........................................

Note that the manual build does not automatically check the
dependencies.  So we assume that you have all the systems requirements
installed.  Steps to manually build from the source distribution:

1. Download the sources.

   From the `Release Page <GitHub latest release_>`_ you may download
   the source distribution file |distribution_source|_ and the
   detached signature file |distribution_signature|_

2. Check the signature (optional).

   You may verify the integrity of the source distribution by checking
   the signature (showing the output for version 0.6 as an example)::

     $ gpg --verify archive-tools-0.6.tar.gz.asc
     gpg: assuming signed data in 'archive-tools-0.6.tar.gz'
     gpg: Signature made Sun Dec 12 15:29:35 2021 CET
     gpg:                using RSA key B4EB920861DF33F31B55A07C08A1264175343E6E
     gpg: Good signature from "Rolf Krahl <rolf@rotkraut.de>" [ultimate]
     gpg:                 aka "Rolf Krahl <rolf@uni-bremen.de>" [ultimate]
     gpg:                 aka "Rolf Krahl <Rolf.Krahl@gmx.net>" [ultimate]

   The signature should be made by the key
   :download:`0xB4EB920861DF33F31B55A07C08A1264175343E6E
   <08A1264175343E6E.pub>`.  The fingerprint of that key is::

     B4EB 9208 61DF 33F3 1B55  A07C 08A1 2641 7534 3E6E

3. Unpack and change into the source directory.

4. Build (optional)::

     $ python setup.py build

5. Test (optional, see below)::

     $ python setup.py test

6. Install::

     $ python setup.py install

The last step might require admin privileges in order to write into
the site-packages directory of your Python installation.


.. _setuptools: https://github.com/pypa/setuptools/
.. _packaging: https://github.com/pypa/packaging/
.. _PyYAML: https://github.com/yaml/pyyaml/
.. _lark: https://github.com/lark-parser/lark
.. _imapclient: https://github.com/mjs/imapclient/
.. _python-dateutil: https://dateutil.readthedocs.io/en/stable/
.. _git-props: https://github.com/RKrahl/git-props/
.. _pytest: https://pytest.org/
.. _distutils-pytest: https://github.com/RKrahl/distutils-pytest/
.. _pytest-dependency: https://github.com/RKrahl/pytest-dependency/
.. _PyPI site: https://pypi.org/project/archive-tools/
.. _GitHub latest release: https://github.com/RKrahl/archive-tools/releases/latest/
