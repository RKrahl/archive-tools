Tools for managing archives
===========================

This package provides tools for managing archives.  An archive in
terms of this package is a (compressed) tar archive file with some
embedded metadata on the included files.  This metadata include the
name, file stats, and checksums of the file.

The package provides a command line tool to work with archives,
including the following tasks:

+ Create an archive, takes a list of files to include in the archive
  as input.

+ Check the integrity and consistency of an archive.

+ List the contents of the archive.

+ Display details on a file in an archive.

+ Given a list of files as input, list those files that are either not
  in the archive or where the file in the archive differs.

Whenever possible, these tasks operate on the embedded metadata in the
archive.  Retrieving this metadata does not require reading through
the compressed tar archive.

Content of the documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   install
   usage
   scripts
   moduleref
   changelog


Indices and tables
==================

* :ref:`genindex`
