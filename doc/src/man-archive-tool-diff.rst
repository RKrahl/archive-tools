archive-tool diff
=================

Synopsis
~~~~~~~~

*archive-tool diff* [--report-meta] [--skip-dir-content] <archive1> <archive2>

Description
~~~~~~~~~~~

.. program:: archive-tool diff

Show the differences between two archives.

Options
~~~~~~~

.. program:: archive-tool diff

.. option:: --report-meta

    Also show differences in file system metadata.

.. option:: --skip-dir-content

    In the case of a subdirectory missing from one archive, only
    report the directory, but skip its content.

.. option:: <archive1>

    Path to the first archive file to compare.

.. option:: <archive2>

    Path to the second archive file to compare.
