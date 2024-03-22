:mod:`archive.archive` --- Provide the Archive class
====================================================

.. py:module:: archive.archive

.. autoclass:: archive.archive.DedupMode
    :members:
    :show-inheritance:

    .. attribute:: NEVER

       never use hard links in the archive

    .. attribute:: LINK

       when already the input files were hard linked to each other in
       the file system

    .. attribute:: CONTENT

       when the input files have the same content

.. autoclass:: archive.archive.Archive
    :members:
    :undoc-members:
    :show-inheritance:
