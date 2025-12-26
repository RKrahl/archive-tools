archive-tool find
=================

Synopsis
~~~~~~~~

*archive-tool find* [--type {f,d,l}] [--name <pattern>] [--mtime <time>]
<archive> [<archive> ...]


Description
~~~~~~~~~~~

.. program:: archive-tool find

Search for entries in archives.


Options
~~~~~~~

.. program:: archive-tool find

.. option:: --type {f,d,l}

    Find entries by type.

.. option:: --name <pattern>

    Find entries whose file name (with leading directories removed)
    matches pattern.

.. option:: --mtime <time>

    Find entries by modification time.

.. option:: <archive>

    Path to the archive file(s) to search entries in.
