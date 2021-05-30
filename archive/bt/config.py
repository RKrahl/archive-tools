"""Configuration for the backup-tool command line tool.
"""

import datetime
import os
from pathlib import Path
import pwd
import socket
import archive.config


def get_config_file():
    try:
        return os.environ['BACKUP_CFG']
    except KeyError:
        return "/etc/backup.cfg"

class Config(archive.config.Config):

    defaults = {
        'dirs': None,
        'excludes': "",
        'backupdir': None,
        'targetdir': "%(backupdir)s",
        'name': "%(host)s-%(date)s-%(schedule)s.tar.bz2",
    }
    args_options = ('policy', 'user', 'schedule')

    def __init__(self, args):
        host = socket.gethostname()
        config_file = get_config_file()
        sections = ("%s/%s" % (host, args.policy), host, args.policy)
        self.config_file = config_file
        super().__init__(args, config_section=sections)
        if not self.config_file:
            raise ConfigError("configuration file %s not found" % config_file)
        self['host'] = host
        self['date'] = datetime.date.today().strftime("%y%m%d")
        if args.user:
            try:
                self['home'] = pwd.getpwnam(args.user).pw_dir
            except KeyError:
                pass

    @property
    def host(self):
        return self.get('host')

    @property
    def policy(self):
        return self.get('policy')

    @property
    def user(self):
        return self.get('user')

    @property
    def schedule(self):
        return self.get('schedule')

    @property
    def name(self):
        return self.get('name', required=True)

    @property
    def dirs(self):
        return self.get('dirs', required=True, split=True, type=Path)

    @property
    def excludes(self):
        return self.get('excludes', split=True, type=Path)

    @property
    def backupdir(self):
        return self.get('backupdir', required=True, type=Path)

    @property
    def targetdir(self):
        return self.get('targetdir', required=True, type=Path)

    @property
    def path(self):
        return self.targetdir / self.name
