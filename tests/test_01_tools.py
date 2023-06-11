"""Test module archive.tools
"""

import packaging.version
import pytest
from archive.tools import *

@pytest.mark.parametrize(("vstr", "checks"), [
    ("4.11.1", [
        (lambda v: v == "4.11.1", True),
        (lambda v: v < "4.11.1", False),
        (lambda v: v > "4.11.1", False),
        (lambda v: v < "5.0.0", True),
        (lambda v: v > "4.11.0", True),
        (lambda v: v > "4.9.3", True),
        (lambda v: v == packaging.version.Version("4.11.1"), True),
    ]),
    ("5.0.0a2", [
        (lambda v: v == "5.0.0", False),
        (lambda v: v < "5.0.0", True),
        (lambda v: v > "4.11.1", True),
        (lambda v: v > "5.0.0a1", True),
        (lambda v: v == "5.0.0a2", True),
        (lambda v: v < "5.0.0b1", True),
    ]),
])
def test_version(vstr, checks):
    """Test class Version.
    """
    version = Version(vstr)
    for check, res in checks:
        assert check(version) == res
