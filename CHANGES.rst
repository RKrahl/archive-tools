History of changes to archive-tools
===================================

dev (not yet released)
    Incompatible changes
      + #23 and #26: review the API of :class:`Archive`:
          - Add two methods :meth:`Archive.create` and
            :meth:`Archive.open` that create and read archives
            respectively.
          - The :meth:`Archive.__init__` method does not create or
            open archives any longer.
          - :meth:`Archive.verify` does not accept the mode argument
            any more.
          - :class:`Archive` keeps a file object to read the tarfile.
            It is opened in :meth:`Archive.open`.
            :meth:`Archive.verify` does not reopen the tarfile, but
            relies on the internal file object to be left open.
          - Add a :meth:`Archive.close` method.
          - :class:`Archive` implements the context manager protocol.
          - add methods :meth:`Archive.add_metadata` and
            :meth:`Archive.get_metadata` to add and to retrieve custom
            metadata to and from archives.

    Bug fixes and minor changes
      + #20: :meth:`Archive.create` takes a working directory as
        optional argument.

0.1 (2019-04-14)
    + Initial release.
