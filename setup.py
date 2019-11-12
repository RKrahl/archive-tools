#! /usr/bin/python
"""Tools for managing archives

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
"""

import distutils.command.build_py
import distutils.command.sdist
import distutils.core
from distutils.core import setup
import distutils.log
from glob import glob
from pathlib import Path
import string
try:
    import distutils_pytest
except ImportError:
    pass
try:
    import setuptools_scm
    version = setuptools_scm.get_version()
    with open(".version", "wt") as f:
        f.write(version)
except (ImportError, LookupError):
    try:
        with open(".version", "rt") as f:
            version = f.read()
    except OSError:
        distutils.log.warn("warning: cannot determine version number")
        version = "UNKNOWN"

doclines = __doc__.strip().split("\n")


class init_py(distutils.core.Command):

    description = "generate the main __init__.py file"
    user_options = []
    init_template = '''"""%s"""

__version__ = "%s"

from archive.archive import Archive
from archive.exception import *
'''

    def initialize_options(self):
        self.packages = None
        self.package_dir = None

    def finalize_options(self):
        self.packages = self.distribution.packages
        self.package_dir = {}
        if self.distribution.package_dir:
            for name, path in self.distribution.package_dir.items():
                self.package_dir[name] = convert_path(path)

    def run(self):
        pkgname = "archive"
        if pkgname not in self.packages:
            raise DistutilsSetupError("Expected package '%s' not found"
                                      % pkgname)
        pkgdir = self.package_dir.get(pkgname, pkgname)
        ver = self.distribution.get_version()
        with Path(pkgdir, "__init__.py").open("wt") as f:
            print(self.init_template % (__doc__, ver), file=f)


class sdist(distutils.command.sdist.sdist):
    def run(self):
        self.run_command('init_py')
        super().run()
        subst = {
            "version": self.distribution.get_version(),
            "url": self.distribution.get_url(),
            "description": self.distribution.get_description(),
            "long_description": self.distribution.get_long_description(),
        }
        for spec in glob("*.spec"):
            with Path(spec).open('rt') as inf:
                with Path(self.dist_dir, spec).open('wt') as outf:
                    outf.write(string.Template(inf.read()).substitute(subst))

class build_py(distutils.command.build_py.build_py):
    def run(self):
        self.run_command('init_py')
        super().run()

setup(
    name = "archive-tools",
    version = version,
    description = doclines[0],
    long_description = "\n".join(doclines[2:]),
    author = "Rolf Krahl",
    author_email = "rolf@rotkraut.de",
    url = "https://github.com/RKrahl/archive-tools",
    license = "Apache-2.0",
    requires = ["PyYAML"],
    packages = ["archive", "archive.cli"],
    scripts = ["scripts/archive-tool.py", "scripts/imap-to-archive.py"],
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: System :: Archiving",
        ],
    cmdclass = {'build_py': build_py, 'sdist': sdist, 'init_py': init_py},
)

