"""Tools for managing archives

This package provides tools for managing archives.  An archive in
terms of this package is a (compressed) tar archive file with some
embedded metadata on the included files.  This metadata include the
name, file stats, and checksums of the file.
"""

from ._meta import version as __version__
from .archive import Archive
from .exception import *
