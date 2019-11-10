"""Provide the subcommands of the archive-tool command line tool.
"""

import archive.cli.create
import archive.cli.verify
import archive.cli.ls
import archive.cli.info
import archive.cli.check


def add_subparsers(argparser):
    subparsers = argparser.add_subparsers(title='subcommands', dest='subcmd')
    archive.cli.create.add_parser(subparsers)
    archive.cli.verify.add_parser(subparsers)
    archive.cli.ls.add_parser(subparsers)
    archive.cli.info.add_parser(subparsers)
    archive.cli.check.add_parser(subparsers)
