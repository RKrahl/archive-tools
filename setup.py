#! /usr/bin/python
"""Archive Tools.

This package provides tools for managing archives.
"""

from distutils.core import setup
import distutils.log
try:
    import distutils_pytest
except ImportError:
    pass
try:
    import setuptools_scm
    version = setuptools_scm.get_version()
    with open(".version", "wt") as f:
        f.write(version)
except ImportError:
    try:
        with open(".version", "rt") as f:
            version = f.read()
    except OSError:
        distutils.log.warn("warning: cannot determine version number")
        version = "UNKNOWN"

doclines = __doc__.strip().split("\n")

setup(
    name = "archive-tools",
    version = version,
    description = doclines[0],
    long_description = "\n".join(doclines[2:]),
    author = "Rolf Krahl",
    author_email = "rolf@rotkraut.de",
    license = "Apache-2.0",
    requires = ["PyYAML"],
    packages = ["archive"],
    scripts = ["scripts/archive-tool.py"],
    classifiers = [
        "Development Status :: 1 - Planning",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Archiving",
        ],
)

