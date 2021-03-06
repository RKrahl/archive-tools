Changelog
=========


0.6 (not yet released)
~~~~~~~~~~~~~~~~~~~~~~

New features
------------

+ `#50`_, `#51`_: Add a header with some metadata to the index in a
  mail archive created by :class:`MailArchive`.

Incompatible changes
--------------------

+ The `comment` keyword argument to :class:`MailArchive` has been
  dropped, ref. `#51`_.

Bug fixes and minor changes
---------------------------

+ `#48`_: Review and standardize some error messages.

.. _#48: https://github.com/RKrahl/archive-tools/pull/48
.. _#50: https://github.com/RKrahl/archive-tools/issues/50
.. _#51: https://github.com/RKrahl/archive-tools/pull/51


0.5.1 (2020-12-12)
~~~~~~~~~~~~~~~~~~

Bug fixes and minor changes
---------------------------

+ `#46`_, `#47`_: `archive-tool` fails with :exc:`NameError` when
  trying to emit a warning.

.. _#46: https://github.com/RKrahl/archive-tools/issues/46
.. _#47: https://github.com/RKrahl/archive-tools/pull/47


0.5 (2020-05-09)
~~~~~~~~~~~~~~~~

New features
------------

+ `#45`_: The files argument to `archive-tool check` defaults to the
  archive's basedir.

Bug fixes and minor changes
---------------------------

+ Fix: some test data have not been included in the source
  distribution.

.. _#45: https://github.com/RKrahl/archive-tools/issues/45


0.4 (2019-12-26)
~~~~~~~~~~~~~~~~

New features
------------

+ `#15`_, `#43`_: Add `archive-tool find` subcommand.

+ `#38`_, `#39`_: Add `archive-tool diff` subcommand.

+ `#40`_, `#44`_: Add setting tags in the header of the manifest.

+ `#41`_: Add a :meth:`Archive.extract` method.

+ Add a :meth:`Manifest.sort` method.

Internal changes
----------------

+ Reorganization of the `archive-tool` script, move the code into
  submodules in the new `archive.cli` package.

.. _#15: https://github.com/RKrahl/archive-tools/issues/15
.. _#38: https://github.com/RKrahl/archive-tools/issues/38
.. _#39: https://github.com/RKrahl/archive-tools/pull/39
.. _#40: https://github.com/RKrahl/archive-tools/issues/40
.. _#41: https://github.com/RKrahl/archive-tools/pull/41
.. _#43: https://github.com/RKrahl/archive-tools/pull/43
.. _#44: https://github.com/RKrahl/archive-tools/pull/44


0.3 (2019-08-06)
~~~~~~~~~~~~~~~~

New features
------------

+ `#33`_: `archive-tool create` should have an option to exclude files.

+ `#35`_: :class:`FileInfo` calculates checksums lazily.

+ `#34`_: files of unsupported type are ignored when creating an
  archive.  A warning is emitted instead of raising an error.

Incompatible changes
--------------------

+ `#36`_: Drop support for strings in the file name arguments `path`,
  `paths`, `basedir`, and `workdir` of the methods
  :meth:`Archive.create` and :meth:`Archive.open`.  These arguments
  require :class:`Path` objects now.

Bug fixes and minor changes
---------------------------

+ `#37`_: `archive-tool create` throws an error when trying to
  explicitly add a symlink.

.. _#33: https://github.com/RKrahl/archive-tools/issues/33
.. _#34: https://github.com/RKrahl/archive-tools/issues/34
.. _#35: https://github.com/RKrahl/archive-tools/issues/35
.. _#36: https://github.com/RKrahl/archive-tools/pull/36
.. _#37: https://github.com/RKrahl/archive-tools/issues/37


0.2 (2019-07-14)
~~~~~~~~~~~~~~~~

New features
------------

+ `#28`_: support deduplication.

+ `#26`_ and `#30`_: add support for custom metadata:

  - Add methods :meth:`Archive.add_metadata` and
    :meth:`Archive.get_metadata` to add and to retrieve custom
    metadata to and from archives.

  - Add a list of metadata items in the header of the manifest.

  - Bump manifest version to 1.1.

+ `#4`_, `#32`_: Add :class:`MailArchive` implementing a special
  flavour of an :class:`Archive` for storing mails.

+ `#27`_: Add command line flags `--prefix <dir>` and `--stdin` to
  `archive-tool check`.

Incompatible changes
--------------------

+ `#23`_ and `#26`_: review the API of :class:`Archive`:

  - Add two methods :meth:`Archive.create` and :meth:`Archive.open`
    that create and read archives respectively.

  - The :meth:`Archive.__init__` method does not create or open
    archives any longer.

  - :meth:`Archive.verify` does not accept the mode argument any more.

  - :class:`Archive` keeps a file object to read the tarfile.  It is
    opened in :meth:`Archive.open`.  :meth:`Archive.verify` does not
    reopen the tarfile, but relies on the internal file object to be
    left open.

  - Add a :meth:`Archive.close` method.

  - :class:`Archive` implements the context manager protocol.

Bug fixes and minor changes
---------------------------

+ `#20`_: :meth:`Archive.create` takes a working directory as optional
  argument.

+ `#29`_: Verify fails if archive contains hard links.

+ `#25`_: `archive-tool check` should ignore metadata.

.. _#4: https://github.com/RKrahl/archive-tools/issues/4
.. _#20: https://github.com/RKrahl/archive-tools/issues/20
.. _#23: https://github.com/RKrahl/archive-tools/issues/23
.. _#25: https://github.com/RKrahl/archive-tools/issues/25
.. _#26: https://github.com/RKrahl/archive-tools/pull/26
.. _#27: https://github.com/RKrahl/archive-tools/issues/27
.. _#28: https://github.com/RKrahl/archive-tools/issues/28
.. _#29: https://github.com/RKrahl/archive-tools/issues/29
.. _#30: https://github.com/RKrahl/archive-tools/pull/30
.. _#32: https://github.com/RKrahl/archive-tools/pull/32


0.1 (2019-04-14)
~~~~~~~~~~~~~~~~

+ Initial release.
