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
from imapclient import IMAPClient
import yaml
from archive import Archive
from archive.tools import tmp_chdir, now_str

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

    def create(self, path, indexfile, 
               compression='xz', paths=None, basedir=None):
        self.add_metadata(".mailindex.yaml", indexfile)
        super().create(path, compression, paths, basedir=basedir)



os.umask(0o077)
with tempfile.TemporaryDirectory(prefix="imap-to-archive-") as tmpdir:
    archive_path = Path.cwd() / args.archive
    with tmp_chdir(tmpdir):
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
        log.debug("%d messages downloaded", len(mailindex))
        with tempfile.TemporaryFile(dir=tmpdir) as tmpf:
            head = """%%YAML 1.1
# Fetched from %s at %s
""" % (args.host, now_str())
            tmpf.write(head.encode("ascii"))
            yaml.dump(mailindex, stream=tmpf, encoding="ascii",
                      default_flow_style=False, explicit_start=True)
            tmpf.seek(0)
            log.debug("writing archive file %s", archive_path)
            archive = MailArchive()
            archive.create(archive_path, tmpf, paths=["Maildir"])
