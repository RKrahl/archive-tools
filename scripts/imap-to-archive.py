#! /usr/bin/python
"""Fetch mail messages from an IMAP4 server and store them into an archive.
"""

import argparse
import getpass
import logging
import os.path
from pathlib import Path
import sys
from imapclient import IMAPClient
import archive.config
from archive.exception import ConfigError
from archive.mailarchive import MailArchive

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logging.getLogger('imapclient').setLevel(logging.WARNING)
log = logging.getLogger(__name__)

security_methods = {'imaps', 'starttls'}
default_config_file = os.path.expanduser("~/.config/archive/imap.cfg")

class Config(archive.config.Config):

    defaults = {
        'host': None,
        'port': None,
        'security': 'imaps',
        'user': None,
        'pass': None,
    }
    args_options = ('host', 'port', 'security', 'user')

    def __init__(self, args):
        self.config_file = args.config_file
        super().__init__(args, config_section=args.config_section)
        if args.config_section:
            if not self.config_file:
                raise ConfigError("configuration file %s not found"
                                  % args.config_file)
            if not self.config_section:
                raise ConfigError("configuration section %s not found"
                                  % args.config_section)
        if self['security'] not in security_methods:
            raise ConfigError("invalid security method '%s'" % self['security'])
        if not self['host']:
            raise ConfigError("IMAP4 host name not specified")
        if self['port'] is not None:
            self['port'] = int(config['port'])
        self['ssl'] = self['security'] == 'imaps'
        if not self['user']:
            raise ConfigError("IMAP4 user name not specified")
        if self['pass'] is None:
            self['pass'] = getpass.getpass()


argparser = argparse.ArgumentParser(add_help=False)
argparser.add_argument('--help',
                       action='help', default=argparse.SUPPRESS,
                       help=('show this help message and exit'))
argparser.add_argument('-c', '--config-file', default=default_config_file,
                       help=("configuration file"))
argparser.add_argument('-s', '--config-section',
                       help=("section in the configuration file"))
argparser.add_argument('-h', '--host',
                       help=("host name of the IMAP4 server"))
argparser.add_argument('-p', '--port', type=int,
                       help=("port of the IMAP4 server"))
argparser.add_argument('--security', choices=security_methods,
                       help=("security method"))
argparser.add_argument('-u', '--user',
                       help=("IMAP4 user name"))
argparser.add_argument('-v', '--verbose', action='store_true',
                       help=("verbose diagnostic output"))
argparser.add_argument('archive', type=Path,
                       help=("path to the archive file"))
args = argparser.parse_args()

if args.verbose:
    logging.getLogger().setLevel(logging.DEBUG)

try:
    config = Config(args)
except ConfigError as e:
    print("%s: configuration error: %s" % (argparser.prog, e), file=sys.stderr)
    sys.exit(2)


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


archive_path = Path.cwd() / args.archive
with IMAPClient(config['host'], port=config['port'], ssl=config['ssl']) as imap:
    if config['security'] == 'starttls':
        imap.starttls()
    imap.login(config['user'], config['pass'])
    log.debug("Login to %s successful", config['host'])
    archive = MailArchive()
    archive.create(archive_path, getmsgs(imap, "INBOX"), server=config['host'])
