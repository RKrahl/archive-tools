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
process with the standard ``tar`` command::

  $ tar tfj bilder-polen.tar.bz2 
  Bilder/.manifest.yaml
  Bilder/Polen/
  Bilder/Polen/.index.yaml
  Bilder/Polen/NOTES
  Bilder/Polen/dsc_3858.jpg
  Bilder/Polen/dsc_3861.jpg
  Bilder/Polen/dsc_3867.jpg
  Bilder/Polen/dsc_3869.jpg
  Bilder/Polen/dsc_3871.jpg
  Bilder/Polen/dsc_3872.jpg
  Bilder/Polen/dsc_3876.jpg
  Bilder/Polen/dsc_3877.jpg
  Bilder/Polen/dsc_3878.jpg
  Bilder/Polen/dsc_3879.jpg
  Bilder/Polen/dsc_3882.jpg
  Bilder/Polen/dsc_3886.jpg

Obviously, you could have achieved almost the same with just the
``tar`` command.  But note the entry ``Bilder/.manifest.yaml`` that
has been added by :ref:`archive-tool`.  This manifest file contains
metadata about the content of the archive that will be used by
:ref:`archive-tool` later on.

List the content of an archive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We can list the content of the archive we just created with::

  $ archive-tool ls bilder-polen.tar.bz2 
  drwxr-xr-x  rolf/users         0  2026-08-17 09:29  Bilder/Polen
  -rw-r--r--  rolf/users     65655  2025-12-24 18:21  Bilder/Polen/.index.yaml
  -rw-r--r--  rolf/users      2080  2025-12-24 18:23  Bilder/Polen/NOTES
  -rw-r--r--  rolf/users   7897273  2025-08-28 09:34  Bilder/Polen/dsc_3858.jpg
  -rw-r--r--  rolf/users   6110268  2025-08-28 09:34  Bilder/Polen/dsc_3861.jpg
  -rw-r--r--  rolf/users   6438806  2025-08-28 09:41  Bilder/Polen/dsc_3867.jpg
  -rw-r--r--  rolf/users   6913762  2025-08-28 09:47  Bilder/Polen/dsc_3869.jpg
  -rw-r--r--  rolf/users   7518441  2025-08-28 09:50  Bilder/Polen/dsc_3871.jpg
  -rw-r--r--  rolf/users   9682781  2025-08-28 10:45  Bilder/Polen/dsc_3872.jpg
  -rw-r--r--  rolf/users  10143308  2025-08-28 11:07  Bilder/Polen/dsc_3876.jpg
  -rw-r--r--  rolf/users  11316528  2025-08-28 11:11  Bilder/Polen/dsc_3877.jpg
  -rw-r--r--  rolf/users   8889209  2025-08-28 11:44  Bilder/Polen/dsc_3878.jpg
  -rw-r--r--  rolf/users  11189580  2025-08-28 11:47  Bilder/Polen/dsc_3879.jpg
  -rw-r--r--  rolf/users   6827151  2025-08-28 13:09  Bilder/Polen/dsc_3882.jpg
  -rw-r--r--  rolf/users   9577664  2025-08-29 10:19  Bilder/Polen/dsc_3886.jpg

This will show mostly the same output that we'd also get with
``tar tfvj bilder-polen.tar.bz2``.  But the latter would need to
(uncompress and) read the whole tar file to create this list, while
:ref:`archive-tool` only needs to read the manifest at the very
beginning of the archive, which may be much quicker for large
archives.

The manifest also contains checksums of the included files that we
also can list::

  $ archive-tool ls --format checksum bilder-polen.tar.bz2 
  3cd3b2ac825c218f8f75be5a733746af04ade5d2345a529fb1bb8b7af7459c00  Bilder/Polen/.index.yaml
  60c21ce2f505383d159158c8975f02ccb43e6e577acc22c9102bad9190a36266  Bilder/Polen/NOTES
  e41024b4542fc183df3a9563165fb030d04368b34c3522b8f446774ec018a540  Bilder/Polen/dsc_3858.jpg
  96c4c601b95c2661366d4a7539b68c67162787e256ef5d458593c456ef765eb5  Bilder/Polen/dsc_3861.jpg
  d212177bccb391e72d87550ded21dc504e0be809ecef21085243c5efebb611dc  Bilder/Polen/dsc_3867.jpg
  3c64756511abafd84830cf8c00284f6232fc3c35f83f5b08d80e1e0bcab88f27  Bilder/Polen/dsc_3869.jpg
  231d19df54066fea3efed098175f20b86278fde1f551fe70732983b61294de2a  Bilder/Polen/dsc_3871.jpg
  b6468278c7aba14eff29679b667568e7352cbfe19d8e31c0a079eeee9a7f7084  Bilder/Polen/dsc_3872.jpg
  197c54fec3682a3ae8164b4bc53db5e00115471a93636166cb30dd5deadd2a9e  Bilder/Polen/dsc_3876.jpg
  130ed37e772ae5c50076b4ae621c304fa6c0cadb52a4db06f1d987e7b8a5e350  Bilder/Polen/dsc_3877.jpg
  56373a664e3f1382ce183971331abd5e13772e81ac8bf86a019cf972fa576f13  Bilder/Polen/dsc_3878.jpg
  dc484c55edb6cbcdc7f3ecc315d21824da93929b1cabe00788c11a3cee5e7ca5  Bilder/Polen/dsc_3879.jpg
  ad320ce0127b71c7ff88cb40a58839f8b6036ef78682256ea5cc3955450971d8  Bilder/Polen/dsc_3882.jpg
  b2cfc5abce0e5a137a829e844ea8b43d64b69e0e291335565dc170ddf0daecd0  Bilder/Polen/dsc_3886.jpg

We could pipe this into ``sha256sum`` to check whether some file in
our directory has changed after we created the archive::

  $ archive-tool ls --format checksum bilder-polen.tar.bz2 | sha256sum --check
  Bilder/Polen/.index.yaml: OK
  Bilder/Polen/NOTES: OK
  Bilder/Polen/dsc_3858.jpg: OK
  Bilder/Polen/dsc_3861.jpg: OK
  Bilder/Polen/dsc_3867.jpg: OK
  Bilder/Polen/dsc_3869.jpg: OK
  Bilder/Polen/dsc_3871.jpg: OK
  Bilder/Polen/dsc_3872.jpg: OK
  Bilder/Polen/dsc_3876.jpg: OK
  Bilder/Polen/dsc_3877.jpg: OK
  Bilder/Polen/dsc_3878.jpg: OK
  Bilder/Polen/dsc_3879.jpg: OK
  Bilder/Polen/dsc_3882.jpg: OK
  Bilder/Polen/dsc_3886.jpg: OK

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
archive or that are changed since they have been archived::

  $ archive-tool check bilder-polen.tar.bz2 Bilder/Polen
  Bilder/Polen/dsc_3888.jpg
  Bilder/Polen/dsc_3890.jpg
  Bilder/Polen/dsc_3858.jpg
  Bilder/Polen/dsc_3869.jpg
  Bilder/Polen/dsc_3871.jpg

Maybe we want to use that to create an update archive::

  $ archive-tool create bilder-polen-update.tar.bz2 $(archive-tool check bilder-polen.tar.bz2 Bilder/Polen)
  $ archive-tool ls bilder-polen-update.tar.bz2
  -rw-r--r--  rolf/users   7897289  2026-08-17 10:38  Bilder/Polen/dsc_3858.jpg
  -rw-r--r--  rolf/users   6913778  2026-08-17 10:38  Bilder/Polen/dsc_3869.jpg
  -rw-r--r--  rolf/users   7518457  2026-08-17 10:38  Bilder/Polen/dsc_3871.jpg
  -rw-r--r--  rolf/users  11376750  2025-08-29 10:24  Bilder/Polen/dsc_3888.jpg
  -rw-r--r--  rolf/users  13409209  2025-08-29 10:24  Bilder/Polen/dsc_3890.jpg

Compare archives
~~~~~~~~~~~~~~~~

Let's assume we created a second archive of our directory including
the changes made above::

  $ archive-tool create bilder-polen-2.tar.bz2 Bilder/Polen

Later on, we might ask: now I have two archives from the same
directory, what is the difference between the two?
:ref:`archive-tool` can compare two archives::

  $ archive-tool diff bilder-polen.tar.bz2 bilder-polen-2.tar.bz2 
  Files bilder-polen.tar.bz2:Bilder/Polen/dsc_3858.jpg and bilder-polen-2.tar.bz2:Bilder/Polen/dsc_3858.jpg differ
  Files bilder-polen.tar.bz2:Bilder/Polen/dsc_3869.jpg and bilder-polen-2.tar.bz2:Bilder/Polen/dsc_3869.jpg differ
  Files bilder-polen.tar.bz2:Bilder/Polen/dsc_3871.jpg and bilder-polen-2.tar.bz2:Bilder/Polen/dsc_3871.jpg differ
  Only in bilder-polen-2.tar.bz2: Bilder/Polen/dsc_3888.jpg
  Only in bilder-polen-2.tar.bz2: Bilder/Polen/dsc_3890.jpg

It tells us exactly the difference: we have three files that are in
both archives but that differ in content and we have two other files
that are only in the second archive and not in the first one.

Find entries in archives
~~~~~~~~~~~~~~~~~~~~~~~~

A similar question as in the last section might be: I have a bunch of
archives, and now I'm searching for a particular file.  Which archive
contains an entry with a given name.  :ref:`archive-tool` can do that
search::

  $ archive-tool find --name dsc_3858.jpg bilder-*.tar.bz2
  bilder-polen-2.tar.bz2:Bilder/Polen/dsc_3858.jpg
  bilder-polen.tar.bz2:Bilder/Polen/dsc_3858.jpg
  bilder-polen-update.tar.bz2:Bilder/Polen/dsc_3858.jpg

::

  $ archive-tool find --name dsc_3888.jpg bilder-*.tar.bz2
  bilder-polen-2.tar.bz2:Bilder/Polen/dsc_3888.jpg
  bilder-polen-update.tar.bz2:Bilder/Polen/dsc_3888.jpg

One can as well search for file patterns::

  $ archive-tool find --name 'dsc_386*.jpg' bilder-*.tar.bz2
  bilder-polen-2.tar.bz2:Bilder/Polen/dsc_3861.jpg
  bilder-polen-2.tar.bz2:Bilder/Polen/dsc_3867.jpg
  bilder-polen-2.tar.bz2:Bilder/Polen/dsc_3869.jpg
  bilder-polen.tar.bz2:Bilder/Polen/dsc_3861.jpg
  bilder-polen.tar.bz2:Bilder/Polen/dsc_3867.jpg
  bilder-polen.tar.bz2:Bilder/Polen/dsc_3869.jpg
  bilder-polen-update.tar.bz2:Bilder/Polen/dsc_3869.jpg
