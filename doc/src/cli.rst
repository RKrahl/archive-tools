Command line scripts
====================

This section provides a reference for the command line scripts that
are installed with archive-tools.

.. _archive-tool:

archive-tool
~~~~~~~~~~~~

The :ref:`archive-tool` script is the major command line interface
that most users will use to create and manage archives.  It provides
the following subcommands:

.. toctree::
   :maxdepth: 1

   man-archive-tool-create
   man-archive-tool-verify
   man-archive-tool-ls
   man-archive-tool-info
   man-archive-tool-check
   man-archive-tool-diff
   man-archive-tool-find

.. _backup-tool:

backup-tool
~~~~~~~~~~~

The :ref:`backup-tool` script is designed to run in the background,
for instance launched regularly by a system timer, to create backups.
Its behavior is controlled with a configuration file.  It provides the
following subcommands:

.. toctree::
   :maxdepth: 1

   man-backup-tool-create
   man-backup-tool-index

.. _imap-to-archive:

imap-to-archive
~~~~~~~~~~~~~~~

The :ref:`imap-to-archive` script fetches mails from an IMAP server
and stores them in an archive.  For the moment, this is implemented as
a proof-of-concept and still experimental.  It is intentionally not
further documented here, as it is not yet stable, its interface may
change or it may be dropped in future versions.
