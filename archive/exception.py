"""Exception handling.
"""

import stat

class _BaseException(Exception):
    """An exception that tries to suppress misleading context.

    `Exception Chaining and Embedded Tracebacks`_ has been introduced
    with Python 3.  Unfortunately the result is completely misleading
    most of the times.  This class supresses the context in
    :meth:`__init__`.

    .. _Exception Chaining and Embedded Tracebacks: https://www.python.org/dev/peps/pep-3134/

    """
    def __init__(self, *args):
        super().__init__(*args)
        if hasattr(self, '__cause__'):
            self.__cause__ = None

class ArgError(_BaseException):
    pass

class ArchiveError(_BaseException):
    pass

class ArchiveCreateError(ArchiveError):
    pass

class ArchiveReadError(ArchiveError):
    pass

class ArchiveIntegrityError(ArchiveError):
    pass

class ArchiveInvalidTypeError(ArchiveError):
    def __init__(self, path, ftype):
        self.path = path
        self.ftype = ftype
        if stat.S_ISFIFO(ftype):
            tstr = "FIFO"
        elif stat.S_ISCHR(ftype):
            tstr = "character device file"
        elif stat.S_ISBLK(ftype):
            tstr = "block device file"
        elif stat.S_ISSOCK(ftype):
            tstr = "socket"
        else:
            tstr = "unsuported type %x" % ftype
        super().__init__("%s: %s" % (str(path), tstr))

class ArchiveWarning(Warning):
    pass
