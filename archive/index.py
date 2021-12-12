"""Provide the ArchiveIndex class that represents an index of archives.
"""

from collections.abc import Mapping, Sequence
from distutils.version import StrictVersion
from pathlib import Path
import yaml
from archive.archive import Archive
from archive.tools import parse_date


class IndexItem:

    def __init__(self, data=None, archive=None):
        if data is not None:
            self.date = parse_date(data['date'])
            self.path = Path(data['path'])
            self.host = data.get('host')
            self.policy = data.get('policy')
            self.user = data.get('user')
            self.schedule = data.get('schedule')
            self.type = data.get('type')
        elif archive is not None:
            self.date = parse_date(archive.manifest.head['Date'])
            self.path = archive.path
            tagmap = dict()
            try:
                tags = archive.manifest.head['Tags']
            except KeyError:
                pass
            else:
                for t in tags:
                    try:
                        k, v = t.split(':')
                    except ValueError:
                        continue
                    tagmap[k] = v
            self.host = tagmap.get('host')
            self.policy = tagmap.get('policy')
            self.user = tagmap.get('user')
            self.schedule = tagmap.get('schedule')
            self.type = tagmap.get('type')
        else:
            raise TypeError("Either data or archive must be provided")

    def as_dict(self):
        """Return a dictionary representation of this objects.
        """
        d = {
            'date': self.date.isoformat(sep=' '),
            'path': str(self.path),
        }
        for k in ('host', 'policy', 'user', 'schedule', 'type'):
            v = getattr(self, k, None)
            if v:
                d[k] = v
        return d

    def __ge__(self, other):
        """self >= other

        Only implemented if other is a mapping.  In this case, return
        True if all key value pair in other are also set in self,
        False otherwise.
        """
        if isinstance(other, Mapping):
            d = self.as_dict()
            for k, v in other.items():
                try:
                    if d[k] != v:
                        return False
                except KeyError:
                    return False
            else:
                return True
        else:
            return NotImplemented

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.as_dict())


class ArchiveIndex(Sequence):

    Version = "1.0"

    def __init__(self, fileobj=None):
        if fileobj is not None:
            docs = yaml.safe_load_all(fileobj)
            self.head = next(docs)
            self.items = [ IndexItem(data=d) for d in next(docs) ]
        else:
            self.head = {
                "Version": self.Version,
            }
            self.items = []

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items.__getitem__(index)

    def append(self, i):
        self.items.append(i)

    @property
    def version(self):
        return StrictVersion(self.head["Version"])

    def find(self, path):
        for i in self:
            if i.path == path:
                return i
        else:
            return None

    def write(self, fileobj):
        fileobj.write("%YAML 1.1\n".encode("ascii"))
        yaml.dump(self.head, stream=fileobj, encoding="ascii",
                  default_flow_style=False, explicit_start=True)
        yaml.dump([ i.as_dict() for i in self ],
                  stream=fileobj, encoding="ascii",
                  default_flow_style=False, explicit_start=True)

    def add_archives(self, paths, prune=False):
        seen = set()
        for p in paths:
            p = p.resolve()
            seen.add(p)
            if self.find(p):
                continue
            with Archive().open(p) as archive:
                self.append(IndexItem(archive=archive))
        if prune:
            items = [ i for i in self if i.path in seen ]
            self.items = items

    def sort(self, *, key=None, reverse=False):
        if key is None:
            key = lambda i: i.date
        self.items.sort(key=key, reverse=reverse)
