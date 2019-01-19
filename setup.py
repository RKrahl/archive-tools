#! /usr/bin/python

from distutils.core import setup
try:
    import distutils_pytest
except ImportError:
    pass
import archive
import re

DOCLINES         = archive.__doc__.strip().split("\n")
DESCRIPTION      = DOCLINES[0]
LONG_DESCRIPTION = "\n".join(DOCLINES[2:])
VERSION          = archive.__version__
AUTHOR           = archive.__author__
m = re.match(r"^(.*?)\s*<(.*)>$", AUTHOR)
(AUTHOR_NAME, AUTHOR_EMAIL) = m.groups() if m else (AUTHOR, None)


setup(
    name = "archive-tools",
    version = VERSION,
    description = DESCRIPTION,
    long_description = LONG_DESCRIPTION,
    author = AUTHOR_NAME,
    author_email = AUTHOR_EMAIL,
    license = "Apache-2.0",
    requires = ["PyYAML"],
    packages = ["archive"],
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

