"""Internal modules used by the backup-tool command line tool.
"""

import argparse
import logging
import sys
from archive.exception import ArchiveError, ConfigError
from archive.bt.config import Config
from archive.bt.create import create


# TODO:
#
# - in the long run, we want to select the schedule (e.g. set the
#   conditions, when to choose which schedule) in the configuration
#   file, and even put the definition and semantics (e.g. which
#   schedules exist and what do they mean) there.  But this seem to be
#   most tricky part of the whole project.  We want to get the basics
#   working first.  So for the moment, we hard code definition and
#   semantics here and select the schedule as a command line argument.
#
# - consider add configuration options for dedup mode and for checksum
#   algorithm.
#
# - consider adding more log messages and logging configuration.

log = logging.getLogger(__name__)
schedules = {'full', 'cumu', 'incr'}

def backup_tool():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    argparser = argparse.ArgumentParser()
    clsgrp = argparser.add_mutually_exclusive_group()
    clsgrp.add_argument('--policy', default='sys')
    clsgrp.add_argument('--user')
    argparser.add_argument('--schedule', choices=schedules, default='full')
    argparser.add_argument('-v', '--verbose', action='store_true',
                           help=("verbose diagnostic output"))
    args = argparser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if args.user:
        args.policy = 'user'

    try:
        config = Config(args)
    except ConfigError as e:
        print("%s: configuration error: %s" % (argparser.prog, e),
              file=sys.stderr)
        sys.exit(2)

    log.info("host:%s, policy:%s", config.host, config.policy)

    try:
        create(config)
    except ArchiveError as e:
        print("%s: error: %s" % (argparser.prog, e), 
              file=sys.stderr)
        sys.exit(1)
