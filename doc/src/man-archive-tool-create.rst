archive-tool create
===================

Synopsis
~~~~~~~~

*archive-tool create* [--directory <directory>] [--tag <tag>]
[--compression {none,gz,bz2,xz}] [--basedir <basedir>]
[--exclude <exclude>] [--deduplicate {never,link,content}]
<archive> <file> [<file> ...]

Description
~~~~~~~~~~~

.. program:: archive-tool create

Create an archive.

Options
~~~~~~~

.. program:: archive-tool create

.. option:: --directory <directory>

    Change to `<directory>` prior creating the archive.

.. option:: --tag <tag>

    Add a user defined tag to the archive header.

.. option:: --compression {none,gz,bz2,xz}

    Select the compression algorithm.

.. option:: --basedir <basedir>

    Set the common base directory for all files in the archive.

.. option:: --exclude <exclude>

    Exclude the path `<exclude>` from the archive.

.. option:: --deduplicate {never,link,content}

    When to use hard links to duplicate files

.. option:: <archive>

    Path to the archive file to be created.

.. option:: <file>

    Path to files to add to the archive.
