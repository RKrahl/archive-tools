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

Create archives.  This is script is intended to be run regularly in a
non-interactive way, for instance from a system timer, to create
backups.  Its behavior is controlled with a configuration file.  It
provides the following subcommands:

.. toctree::
   :maxdepth: 1

   man-backup-tool-create
   man-backup-tool-index

.. _imap-to-archive:

imap-to-archive
~~~~~~~~~~~~~~~

This script is experimental and basically just a prove of concept for
now.  It is intentionally not further documented here, as it is not
yet stable, its interface may change or it may be dropped in future
versions.
