#! /usr/bin/python
"""Fetch mail messages from an IMAP4 server and store them into an archive.
"""

import argparse
import datetime
import getpass
import hashlib
import logging
from mailbox import Maildir
import os
from pathlib import Path
import stat
import tempfile
import dateutil.tz
from imapclient import IMAPClient
import yaml
from archive import Archive

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

class MailArchive(Archive):

    def __init__(self, path, indexfile, mode='x:xz', paths=None, basedir=None):
        self.indexfile = indexfile
        super().__init__(path, mode=mode, paths=paths, basedir=basedir)

    def metadata_hook(self, tarf):
        mailindex_name = str(self.basedir / ".mailindex.yaml")
        mailindex_info = tarf.gettarinfo(arcname=mailindex_name, 
                                         fileobj=self.indexfile)
        mailindex_info.mode = stat.S_IFREG | 0o400
        tarf.addfile(mailindex_info, tmpf)

rfc2822_datefmt = "%a, %d %b %Y %H:%M:%S %z"
now = datetime.datetime.now(tz=dateutil.tz.gettz())

os.umask(0o077)
with tempfile.TemporaryDirectory(prefix="imap-to-archive-") as tmpdir:
    os.chdir(tmpdir)
    maildir = Maildir("Maildir", create=True)
    mailindex = []
    with IMAPClient(args.host, ssl=False) as imap:
        imap.starttls()
        imap.login(args.user, getpass.getpass())
        log.debug("Login to %s successful", args.host)
        folders = imap.list_folders(directory="INBOX")
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
            mailfolder = maildir.add_folder(mailfolder_name)
            for n in msgs:
                data = imap.fetch(n, 'RFC822')
                msgbytes = data[n][b'RFC822']
                sha256 = hashlib.sha256(msgbytes).hexdigest()
                key = mailfolder.add(msgbytes)
                msg = mailfolder.get_message(key)
                idx_item = {
                    "Date": msg.get("Date"),
                    "From": msg.get("From"),
                    "MessageId": msg.get("Message-Id"),
                    "Subject": msg.get("Subject"),
                    "To": msg.get("To"),
                    "checksum": { "sha256": sha256 },
                    "folder": mailfolder_name,
                    "key": key,
                }
                mailindex.append(idx_item)
    with tempfile.TemporaryFile(dir=tmpdir) as tmpf:
        head = """%%YAML 1.1
# Fetched from %s at %s
""" % (args.host, now.strftime(rfc2822_datefmt))
        tmpf.write(head.encode("ascii"))
        yaml.dump(mailindex, stream=tmpf, encoding="ascii",
                  default_flow_style=False, explicit_start=True)
        tmpf.seek(0)
        archive = MailArchive(args.archive, tmpf, paths=["Maildir"])
    os.chdir("/")
