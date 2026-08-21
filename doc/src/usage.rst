Using archive-tools
===================

In this section, we provide an overview on how :ref:`archive-tool` is
used.

Create an archive
~~~~~~~~~~~~~~~~~

Let's assume you have some files in a subdirectory ``Bilder/Polen``
that you would like to archive.  You can do this with the following
command::

  $ archive-tool create bilder-polen.tar.bz2 Bilder/Polen

This will create an archive ``bilder-polen.tar.bz2`` with the content
of that directory.  This archive is a normal tar file that you can
process with the standard ``tar`` command:

.. literalinclude:: tar-tfj.snip

Obviously, you could have achieved almost the same with just the
``tar`` command.  But note the entry ``Bilder/.manifest.yaml`` that
has been added by :ref:`archive-tool`.  This manifest file contains
metadata about the content of the archive that will be used by
:ref:`archive-tool` later on.

List the content of an archive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We can list the content of the archive we just created with:

.. literalinclude:: archive-tool-ls.snip

This will show mostly the same output that we'd also get with
``tar tfvj bilder-polen.tar.bz2``.  But the latter would need to
(uncompress and) read the whole tar file to create this list, while
:ref:`archive-tool` only needs to read the manifest at the very
beginning of the archive, which may be much quicker for large
archives.

The manifest also contains checksums of the included files that we can
list as well:

.. literalinclude:: archive-tool-ls-checksum.snip

We could pipe this into ``sha256sum`` to check whether some file in
our directory has changed after we created the archive:

.. literalinclude:: archive-tool-ls-checksum-verify.snip

Check the integrity of an archive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We can use the embedded checksums to check the integrity of the
archive::

  $ archive-tool verify bilder-polen.tar.bz2 && echo Ok
  Ok

Check whether some files are in an archive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's assume we edited some of the images in our directory and added a
few more.  A rather common question in these situations is: which of
the files in my directory are already in the archive?
:ref:`archive-tool` has a subcommand to answer that question.  The
following command will list all files that are either not in the
archive or that are changed since they have been archived:

.. literalinclude:: archive-tool-check.snip

Maybe we want to use that to create an update archive:

.. literalinclude:: archive-tool-check-create.snip

Compare archives
~~~~~~~~~~~~~~~~

Let's assume we created a second archive of our directory including
the changes made above::

  $ archive-tool create bilder-polen-2.tar.bz2 Bilder/Polen

Later on, we might ask: now I have two archives from the same
directory, what is the difference between the two?
:ref:`archive-tool` can compare two archives:

.. literalinclude:: archive-tool-diff.snip

It tells us exactly the difference: we have three files that are in
both archives but that differ in content and we have two other files
that are only in the second archive and not in the first one.

Find entries in archives
~~~~~~~~~~~~~~~~~~~~~~~~

A similar question as in the last section might be: I have a bunch of
archives, and now I'm searching for a particular file.  Which archive
contains an entry with a given name.  :ref:`archive-tool` can do that
search:

.. literalinclude:: archive-tool-find-1.snip

.. literalinclude:: archive-tool-find-2.snip

It is also possible to use a file pattern in the name argument:

.. literalinclude:: archive-tool-find-3.snip
