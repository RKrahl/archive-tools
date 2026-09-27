archive-tool check
==================

Synopsis
~~~~~~~~

*archive-tool check* [--prefix <prefix>] [--present] [--stdin]
<archive> [file ...]

Description
~~~~~~~~~~~

.. program:: archive-tool check

Check if files are in the archive.

Options
~~~~~~~

.. program:: archive-tool check

.. option:: --prefix <prefix>

    Prefix for the path in the archive of files to be checked.

.. option:: --present

    Show files present in the archive, rather then missing ones.

.. option:: --stdin

    Read files to be checked from stdin, rather then from the command
    line.

.. option:: <archive>

    Path to the archive file.
