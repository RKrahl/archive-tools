backup.cfg - backup-tool configuration file
===========================================

Synopsis
~~~~~~~~

**/etc/backup.cfg**

Description
~~~~~~~~~~~

This file controls the behaviour of the :ref:`backup-tool` script.  The
file format is an INI style configuration file as read by
:mod:`configparser`.

The configuration options are listed below.  Most of them are read
from the configuration file, but some are prescribed by the context of
the invocation.

The options are looked up in one or more sections in the configuration
file, depending on context: the :ref:`backup-tool-create` subcommand
checks the sections `[<host>/<policy>]`, `[<host>]`, and `[<policy>]`
in that order, where `<host>` and `<policy>` are the values for the
prescribed options described below.  The :ref:`backup-tool-index`
subcommand only checks the `[<host>]` section.  For each option, the
first value found is used.

The definition of an option in the configuration file may contain
format strings which refer to other options.  This works in a similar
way as the interpolation done by :class:`configparser.BasicInterpolation`,
with the exception that the other option may also be defined in a
different section of the configuration file or may be a prescribed
option.

Note: most options are actually only relevant for
:ref:`backup-tool-create`.  The :ref:`backup-tool-index` subcommand
only needs the `backupdir` option.

Options
~~~~~~~

Prescribed options for all subcommands
......................................

The following options are defined by the context of the invocation of
`backup-tool` and are not read from the configuration file.

.. option:: host

    the host name as returned by :func:`socket.gethostname`.

.. option:: date

    the current date in the format `yymmdd`.

Prescribed options for backup-tool create
.........................................

As for the previous section, the following options are defined by the
context of the invocation of `backup-tool` and are not read from
configuration file.  But they are only defined in
:ref:`backup-tool-create`.

.. option:: policy

    the value of the `--policy` command line option.

.. option:: user

    the value of the `--user` command line option, if given, undefined
    otherwise.

.. option:: home

    the home directory of the user if `user` is defined, undefined
    otherwise.

.. option:: schedule

    the name of the selected schedule.  This is one of the `schedules`
    given in the configuration file below.

Options read from the configuration file
........................................

.. option:: dirs

    Required.  The list of directories to include in the backup.

.. option:: excludes

    List of path names to exclude from the backup.  The default is an
    empty list.

.. option:: backupdir

    Required.  The directory to lookup previous backups.

.. option:: targetdir

    The directory where to create the backup.  The default is the
    value of `backupdir`.

.. option:: name

    The name of the backup to create.  The default is
    `%(host)s-%(date)s-%(schedule)s.tar.bz2`.

.. option:: schedules

    Required.  The list of schedules to consider, separated by a `'/'`
    character.  Each entry may either be a `name` and a `type`
    separated by a `':'` character or just a `type` that is than also
    taken as the `name`.  The `type` must be one out of `full`,
    `cumu`, and `incr`.

.. option:: schedule.<n>.date

    Required for each schedule name `<n>` listed in `schedules`.  A
    date expression when this schedule may be invoked.

.. option:: dedup

    When to use hard links to duplicate files in the backup.  Must be
    one out of `never`, `link`, and `content`.  The default is `link`.
