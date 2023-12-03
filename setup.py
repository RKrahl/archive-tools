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

import setuptools
from setuptools import setup
import setuptools.command.build_py
import distutils.command.sdist
from distutils import log
from glob import glob
from pathlib import Path
import string
try:
    import distutils_pytest
    cmdclass = distutils_pytest.cmdclass
except (ImportError, AttributeError):
    cmdclass = dict()
try:
    import setuptools_scm
    version = setuptools_scm.get_version()
except (ImportError, LookupError):
    try:
        import _meta
        version = _meta.version
    except ImportError:
        log.warn("warning: cannot determine version number")
        version = "UNKNOWN"

docstring = __doc__


class meta(setuptools.Command):

    description = "generate meta files"
    user_options = []
    init_template = '''"""%(doc)s"""

__version__ = "%(version)s"

from archive.archive import Archive
from archive.exception import *
'''
    meta_template = '''
version = "%(version)s"
'''

    def initialize_options(self):
        self.package_dir = None

    def finalize_options(self):
        self.package_dir = {}
        if self.distribution.package_dir:
            for name, path in self.distribution.package_dir.items():
                self.package_dir[name] = convert_path(path)

    def run(self):
        version = self.distribution.get_version()
        log.info("version: %s", version)
        values = {
            'version': version,
            'doc': docstring,
        }
        try:
            pkgname = self.distribution.packages[0]
        except IndexError:
            log.warn("warning: no package defined")
        else:
            pkgdir = Path(self.package_dir.get(pkgname, pkgname))
            if not pkgdir.is_dir():
                pkgdir.mkdir()
            with (pkgdir / "__init__.py").open("wt") as f:
                print(self.init_template % values, file=f)
        with Path("_meta.py").open("wt") as f:
            print(self.meta_template % values, file=f)


# Note: Do not use setuptools for making the source distribution,
# rather use the good old distutils instead.
# Rationale: https://rhodesmill.org/brandon/2009/eby-magic/
class sdist(distutils.command.sdist.sdist):
    def run(self):
        self.run_command('meta')
        super().run()
        subst = {
            "version": self.distribution.get_version(),
            "url": self.distribution.get_url(),
            "description": docstring.split("\n")[0],
            "long_description": docstring.split("\n", maxsplit=2)[2].strip(),
        }
        for spec in glob("*.spec"):
            with Path(spec).open('rt') as inf:
                with Path(self.dist_dir, spec).open('wt') as outf:
                    outf.write(string.Template(inf.read()).substitute(subst))


class build_py(setuptools.command.build_py.build_py):
    def run(self):
        self.run_command('meta')
        super().run()


with Path("README.rst").open("rt", encoding="utf8") as f:
    readme = f.read()

setup(
    name = "archive-tools",
    version = version,
    description = docstring.split("\n")[0],
    long_description = readme,
    long_description_content_type = "text/x-rst",
    url = "https://github.com/RKrahl/archive-tools",
    author = "Rolf Krahl",
    author_email = "rolf@rotkraut.de",
    license = "Apache-2.0",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Archiving",
    ],
    project_urls = dict(
        Source="https://github.com/RKrahl/archive-tools",
        Download="https://github.com/RKrahl/archive-tools/releases/latest",
    ),
    packages = ["archive", "archive.cli", "archive.bt"],
    python_requires = ">=3.6",
    install_requires = ["PyYAML", "packaging", "lark"],
    scripts = ["scripts/archive-tool.py", "scripts/backup-tool.py",
               "scripts/imap-to-archive.py"],
    data_files = [("/etc", ["etc/backup.cfg"])],
    cmdclass = dict(cmdclass, build_py=build_py, sdist=sdist, meta=meta),
)
