History of changes to archive-tools
===================================

dev (not yet released)
    Incompatible changes
      + Issue #23: review the API of :class:`Archive`:
          - Add two class methods :meth:`Archive.create` and
            :meth:`Archive.open` that create :class:`Archive` objects.
          - The :meth:`Archive.__init__` method does not create or
            open archives any longer and is not supposed to be called
            directly.
          - :meth:`Archive.verify` does not accept the mode argument
            any more.
          - :class:`Archive` keeps a file object to read the tarfile.
            It is opened in :meth:`Archive.open`.
            :meth:`Archive.verify` does not reopen the tarfile, but
            relies on the internal file object to be left open.
          - Add a :meth:`Archive.close` method.
          - :class:`Archive` implements the context manager protocol.

    Bug fixes and minor changes
      + Issue #20: :meth:`Archive.create` takes a working directory as
	optional argument.

0.1 (2019-04-14)
    + Initial release.
