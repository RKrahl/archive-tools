from distutils.version import StrictVersion
import hashlib
from mailbox import Maildir
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
import yaml
from archive import Archive
from archive.tools import now_str, parse_date, tmp_chdir, tmp_umask


class MailIndex(list):

    Version = "1.1"

    def __init__(self, fileobj=None, items=None, server=None):
        if fileobj:
            docs = yaml.safe_load_all(fileobj)
            try:
                head = next(docs)
                items = next(docs)
            except StopIteration:
                items = head
                head = dict(Version="1.0")
            super().__init__(items)
            self.head = head
        else:
            if items:
                super().__init__(items)
            else:
                super().__init__()
            self.head = {
                "Date": now_str(),
                "Version": self.Version,
            }
            if server:
                self.head["Server"] = server

    @property
    def version(self):
        return StrictVersion(self.head["Version"])

    @property
    def date(self):
        return parse_date(self.head["Date"])

    def write(self, fileobj):
        fileobj.write("%YAML 1.1\n".encode("ascii"))
        yaml.dump(self.head, stream=fileobj, encoding="ascii",
                  default_flow_style=False, explicit_start=True)
        yaml.dump(list(self), stream=fileobj, encoding="ascii",
                  default_flow_style=False, explicit_start=True)


class MailArchive(Archive):

    def create(self, path, mails, compression='xz', server=None):
        path = Path.cwd() / path
        with TemporaryDirectory(prefix="mailarchive-") as tmpdir:
            with tmp_chdir(tmpdir), tmp_umask(0o077):
                basedir = Path(path.name.split('.')[0])
                maildir = Maildir(basedir, create=True)
                self.mailindex = MailIndex(server=server)
                last_folder = None
                for folder, msgbytes in mails:
                    if folder != last_folder:
                        mailfolder = maildir.add_folder(folder)
                        last_folder = folder
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
                        "folder": folder,
                        "key": key,
                    }
                    self.mailindex.append(idx_item)
                with TemporaryFile(dir=tmpdir) as tmpf:
                    self.mailindex.write(tmpf)
                    tmpf.seek(0)
                    self.add_metadata(".mailindex.yaml", tmpf)
                    super().create(path, compression, [basedir])
        return self

    def open(self, path):
        super().open(path)
        md = self.get_metadata(".mailindex.yaml")
        self.mailindex = MailIndex(fileobj=md.fileobj)
        return self
