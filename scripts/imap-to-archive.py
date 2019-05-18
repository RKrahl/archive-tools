#! /usr/bin/python
"""Fetch mail messages from an IMAP4 server and store them into an archive.
"""

import argparse
import getpass
import logging
import os
from pathlib import Path
from imapclient import IMAPClient
from archive.mailarchive import MailArchive
from archive.tools import now_str

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

logging.getLogger('imapclient').setLevel(logging.WARNING)

# FIXME: should have a more decent configuration:
# - There should be a configuration file, so that not everything need
#   to be set on the command line.
# - Several things are still hard coded in the script that should be
#   configurable.

argparser = argparse.ArgumentParser()
argparser.add_argument('host',
                       help=("host name of the IMAP4 server"))
argparser.add_argument('user',
                       help=("IMAP4 user name"))
argparser.add_argument('archive',
                       help=("path to the archive file"), type=Path)
args = argparser.parse_args()

log = logging.getLogger(__name__)


def getmsgs(imap, basedir):
    """Fetch all messages from an IMAP server, return `(folder, msg)` tuples.
    """
    count = 0
    folders = imap.list_folders(directory=basedir)
    for _, delimiter, folder in folders:
        log.debug("Considering folder %s", folder)
        imap.select_folder(folder, readonly=True)
        msgs = imap.search()
        log.debug("%d messages in folder %s", len(msgs), folder)
        if len(msgs) == 0:
            continue
        delimiter = delimiter.decode("ascii")
        if delimiter == ".":
            mailfolder_name = folder
        else:
            mailfolder_name = folder.replace(delimiter, ".")
        for n in msgs:
            data = imap.fetch(n, 'RFC822')
            msgbytes = data[n][b'RFC822']
            yield (mailfolder_name, msgbytes)
            count += 1
    log.debug("%d messages downloaded", count)


os.umask(0o077)
archive_path = Path.cwd() / args.archive
with IMAPClient(args.host, ssl=False) as imap:
    imap.starttls()
    imap.login(args.user, getpass.getpass())
    log.debug("Login to %s successful", args.host)
    comment = "Fetched from %s at %s" % (args.host, now_str())
    archive = MailArchive()
    archive.create(archive_path, getmsgs(imap, "INBOX"), comment=comment)

