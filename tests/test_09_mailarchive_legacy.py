"""Test reading mail archive from legacy version.
"""

import pytest
from archive.mailarchive import MailArchive
from conftest import gettestdata

@pytest.fixture(scope="module")
def legacy_1_0_archive():
    return gettestdata("mailarchive-legacy-1_0.tar.xz")

def test_1_0_check_mailindex(legacy_1_0_archive):
    with MailArchive().open(legacy_1_0_archive) as archive:
        archive.verify()
        assert archive.mailindex.head
        assert archive.mailindex.version == "1.0"
