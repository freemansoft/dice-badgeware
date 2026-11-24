"""Tests for tools/badge_check.py: the pure logic behind checking the
installed copy from the badge's side after an install. Nothing here
touches a real badge. (Adapted from freemansoft/MoodBadger2350.)"""

import sys

import pytest
from conftest import ROOT, assert_micropython_syntax

sys.path.insert(0, str(ROOT / "tools"))
import badge_check


def test_files_snippet_is_valid_micropython_syntax(tmp_path):
    assert_micropython_syntax(badge_check.FILES_SNIPPET, tmp_path)
    assert '"/system/apps/dice_roller"' in badge_check.FILES_SNIPPET


def test_local_files_are_what_install_copies_with_sizes(tmp_path):
    (tmp_path / "game").mkdir()
    (tmp_path / "__init__.py").write_text("app")
    (tmp_path / "game" / "dice.py").write_bytes(b"12345")
    (tmp_path / "._junk").write_bytes(b"x")
    (tmp_path / "game" / "__pycache__").mkdir()
    (tmp_path / "game" / "__pycache__" / "dice.cpython-311.pyc").write_bytes(b"pyc")
    assert badge_check.local_files(tmp_path) == {"__init__.py": 3, "game/dice.py": 5}


def test_compare_files_reports_missing_extra_size_and_junk():
    local = {"__init__.py": 3, "game/dice.py": 5, "game/app.py": 9}
    badge = {"__init__.py": 3, "game/dice.py": 4096, "old.py": 1, "._icon.png": 4096,
             "game/__pycache__/x.mpy": 7}
    assert badge_check.compare_files(local, badge) == {
        "missing": ["game/app.py"],
        "different size": ["game/dice.py"],
        "not in the app": ["old.py"],
        "macOS junk": ["._icon.png", "game/__pycache__/x.mpy"],
    }


def test_parse_tagged_line():
    out = 'noise\nBADGE_CHECK {"files": {"a.py": 1}}\n'
    assert badge_check.parse_tagged(out) == {"files": {"a.py": 1}}
    with pytest.raises(ValueError):
        badge_check.parse_tagged("no tag here")


def test_mpremote_command_ends_with_a_reset():
    cmd = badge_check.mpremote_command("/dev/x", badge_check.FILES_SNIPPET)
    assert cmd[:3] == ["mpremote", "connect", "/dev/x"] and cmd[-1] == "reset"


def test_check_files_reports_a_match_and_a_short_file(tmp_path, monkeypatch, capsys):
    (tmp_path / "__init__.py").write_text("app")
    monkeypatch.setattr(badge_check, "read", lambda _port, _snippet: {"files": {"__init__.py": 3}})
    badge_check.check_files("/dev/x", src=tmp_path)
    assert "The badge's copy matches." in capsys.readouterr().out

    monkeypatch.setattr(badge_check, "read", lambda _port, _snippet: {"files": {"__init__.py": 1}})
    with pytest.raises(SystemExit):
        badge_check.check_files("/dev/x", src=tmp_path)
    assert "different size: __init__.py" in capsys.readouterr().out


def test_check_files_says_when_the_app_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(badge_check, "read", lambda _port, _snippet: {"files": None})
    with pytest.raises(SystemExit, match="isn't installed"):
        badge_check.check_files("/dev/x", src=tmp_path)
