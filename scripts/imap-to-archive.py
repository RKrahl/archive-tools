#! /usr/bin/python
"""Fetch mail messages from an IMAP4 server and store them into an archive.
"""

import argparse
from collections import ChainMap
import configparser
import getpass
import logging
import os.path
from pathlib import Path
import sys
from imapclient import IMAPClient
from archive.mailarchive import MailArchive
from archive.tools import now_str

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logging.getLogger('imapclient').setLevel(logging.WARNING)
log = logging.getLogger(__name__)

security_methods = {'imaps', 'starttls'}

default_config_file = os.path.expanduser("~/.config/archive/imap.cfg")
defaults = {
    'host': None,
    'port': None,
    'security': 'imaps',
    'user': None,
    'pass': None,
}

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

class ConfigError(Exception):
    pass

def get_config(args, defaults):
    args_cfg_options = ('host', 'port', 'security', 'user')
    args_cfg = { k:vars(args)[k] for k in args_cfg_options if vars(args)[k] }
    config = ChainMap({}, args_cfg)
    if args.config_section:
        cp = configparser.ConfigParser()
        if not cp.read(args.config_file):
            raise ConfigError("configuration file %s not found"
                              % args.config_file)
        try:
            config.maps.append(cp[args.config_section])
        except KeyError:
            raise ConfigError("configuration section %s not found"
                              % args.config_section)
    config.maps.append(defaults)

    if config['security'] not in security_methods:
        raise ConfigError("invalid security method '%s'" % config['security'])
    if not config['host']:
        raise ConfigError("IMAP4 host name not specified")
    if config['port'] is not None:
        config['port'] = int(config['port'])
    config['ssl'] = config['security'] == 'imaps'
    if not config['user']:
        raise ConfigError("IMAP4 user name not specified")
    if config['pass'] is None:
        config['pass'] = getpass.getpass()

    return config

try:
    config = get_config(args, defaults)
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
    comment = "Fetched from %s at %s" % (config['host'], now_str())
    archive = MailArchive()
    archive.create(archive_path, getmsgs(imap, "INBOX"), comment=comment)

