History of changes to archive-tools
===================================

dev (not yet released)
    New features
      + #35: class FileInfo calculates checksums lazily.

0.2 (2019-07-14)
    New features
      + #28: support deduplication.
      + #26 and #30: add support for custom metadata:
	  - Add methods :meth:`Archive.add_metadata` and
            :meth:`Archive.get_metadata` to add and to retrieve custom
            metadata to and from archives.
	  - Add a list of metadata items in the header of the
            manifest.
	  - Bump manifest version to 1.1.
      + #4, #32: Add :class:`MailArchive` implementing a special
        flavour of an :class:`Archive` for storing mails.
      + #27: Add command line flags `--prefix <dir>` and `--stdin` to
	`archive-tool check`.

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

    Bug fixes and minor changes
      + #20: :meth:`Archive.create` takes a working directory as
        optional argument.
      + #29: Verfiy fails if archive contains hard links.
      + #25: `archive-tool check` should ignore metadata.

0.1 (2019-04-14)
    + Initial release.
