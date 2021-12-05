"""Test creating a mail archive and check its content.
"""

import datetime
import email
import pytest
from pytest_dependency import depends
import yaml
from archive import Archive
from archive.mailarchive import MailIndex, MailArchive
from conftest import gettestdata

testdata = gettestdata("mails.tar.gz")
testmails = []

def getmsgs():
    """Yield a couple of test mails along with appropriate folder names.
    """
    mails = Archive().open(testdata)
    idx = yaml.safe_load(mails.get_metadata(".index.yaml").fileobj)
    for folder in sorted(idx.keys()):
        for msg_path in idx[folder]:
            msgbytes = mails._file.extractfile(msg_path).read()
            msg = email.message_from_bytes(msgbytes)
            testmails.append( (folder, msg) )
            yield (folder, msgbytes)

@pytest.fixture(scope="module", params=[ "abs", "rel" ])
def testcase(request):
    param = request.param
    return param

@pytest.fixture(scope="module")
def dep_testcase(request, testcase):
    depends(request, ["test_create_mailarchive[%s]" % testcase])
    return testcase


@pytest.mark.dependency()
def test_create_mailarchive(tmpdir, monkeypatch, testcase):
    if testcase == "abs":
        archive_path = tmpdir / "mailarchive-abs.tar.xz"
    else:
        monkeypatch.chdir(tmpdir)
        archive_path = "mailarchive-rel.tar.xz"
    archive = MailArchive()
    archive.create(archive_path, getmsgs(), server="imap.example.org")

@pytest.mark.dependency()
def test_verify_mailarchive(tmpdir, dep_testcase):
    archive_path = tmpdir / ("mailarchive-%s.tar.xz" % dep_testcase)
    with MailArchive().open(archive_path) as archive:
        archive.verify()

@pytest.mark.dependency()
def test_check_mailindex(tmpdir, dep_testcase):
    archive_path = tmpdir / ("mailarchive-%s.tar.xz" % dep_testcase)
    with MailArchive().open(archive_path) as archive:
        for t, item in zip(testmails, archive.mailindex):
            folder, msg = t
            assert item['Date'] == msg['Date']
            assert item['From'] == msg['From']
            assert item['MessageId'] == msg['Message-Id']
            assert item['Subject'] == msg['Subject']
            assert item['To'] == msg['To']
            assert item['folder'] == folder

@pytest.mark.dependency()
def test_check_mailindex_head(tmpdir, dep_testcase):
    archive_path = tmpdir / ("mailarchive-%s.tar.xz" % dep_testcase)
    with MailArchive().open(archive_path) as archive:
        assert archive.mailindex.head
        assert set(archive.mailindex.head.keys()) == {
            "Date", "Server", "Version"
        }
        assert isinstance(archive.mailindex.date, datetime.datetime)
        assert archive.mailindex.version == MailIndex.Version

@pytest.mark.dependency()
def test_check_mail_messages(tmpdir, dep_testcase):
    archive_path = tmpdir / ("mailarchive-%s.tar.xz" % dep_testcase)
    with MailArchive().open(archive_path) as archive:
        for t, item in zip(testmails, archive.mailindex):
            folder, msg = t
            path = archive.basedir / ("." + folder) / "new" / item['key']
            msgbytes = archive._file.extractfile(str(path)).read()
            assert msgbytes == msg.as_bytes()
