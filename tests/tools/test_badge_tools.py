"""Tests for the firmware tools in tools/: the pure logic that the
badge-firmware and badge-deploy skills rely on. Nothing here touches a
real badge, USB drive or the network. (Adapted from
freemansoft/MoodBadger2350.)"""

import re
import sys

import pytest
from conftest import ROOT, assert_micropython_syntax

sys.path.insert(0, str(ROOT / "tools"))
import badge_info
import badgeware_release as rel
import flash_firmware

# `mpremote devs` on a desk with a Tufty, a Particle board and Bluetooth ports.
DEVS = """\
/dev/cu.BoseQC45 None 0000:0000 None None
/dev/cu.debug-console None 0000:0000 None None
/dev/cu.usbmodem201401 bb713395bda7b3ab 2e8a:1101 Pimoroni Pimoroni Tufty 2350 MicroPython
/dev/cu.usbmodem20111101 e00fce68115b752338ceb4ef 2b04:c00d Particle Boron CDC Mode
"""


# --- badgeware_release -------------------------------------------------------

def test_badge_ports_finds_only_badges():
    assert rel.badge_ports(DEVS) == [("/dev/cu.usbmodem201401", "tufty")]


def test_badge_ports_finds_a_badger_and_a_tufty():
    devs = DEVS + "/dev/cu.usbmodem1101 abc 2e8a:1101 Pimoroni Pimoroni Badger 2350 MicroPython\n"
    assert rel.badge_ports(devs) == [
        ("/dev/cu.usbmodem201401", "tufty"), ("/dev/cu.usbmodem1101", "badger")]


def test_pick_asset_chooses_the_flavour_and_explains_a_miss():
    release = {"tag_name": "v3.1.1", "assets": [
        {"name": "badger-v3.1.1-micropython-with-filesystem.uf2"},
        {"name": "badger-v3.1.1-micropython.uf2"}]}
    assert rel.pick_asset(release, "badger", False)["name"] == "badger-v3.1.1-micropython.uf2"
    assert rel.pick_asset(release, "badger", True)["name"].endswith("-with-filesystem.uf2")
    with pytest.raises(LookupError, match="tufty-v3.1.1-micropython.uf2"):
        rel.pick_asset(release, "tufty", False)


def test_build_date_comes_from_the_micropython_version():
    version = "v1.29.0-gc on 2026-09-23 (GNU 14.2.1 MinSizeRel)"
    assert rel.build_date(version) == "2026-09-23"
    assert rel.build_date("no date here") is None


@pytest.mark.parametrize(("built", "published", "status"), [
    ("2026-09-23", "2026-09-23T12:11:22Z", "current"),
    ("2026-09-21", "2026-09-23T12:11:22Z", "current"),
    ("2026-09-14", "2026-09-23T12:11:22Z", "older"),
    ("2026-10-05", "2026-09-23T12:11:22Z", "newer"),
    (None, "2026-09-23T12:11:22Z", "unknown"),
])
def test_firmware_status_compares_build_and_release_dates(built, published, status):
    assert rel.firmware_status(built, published) == status


def test_is_uf2_checks_the_block_magic():
    assert rel.is_uf2(b"UF2\n\x57\x51\x5d\x9e" + b"\0" * 24)
    assert not rel.is_uf2(b"<html>not a uf2 file")


def test_find_volumes_matches_labels_case_insensitively(tmp_path):
    (tmp_path / "BADGER").mkdir()
    (tmp_path / "Tufty2350").mkdir()
    (tmp_path / "Macintosh HD").mkdir()
    found = rel.find_volumes(("BADGER", "TUFTY2350"), bases=[tmp_path])
    assert sorted(p.name for p in found) == ["BADGER", "Tufty2350"]


def test_mpremote_is_found_for_this_python():
    # requirements-dev.txt installs it into .venv, which runs these tests;
    # the tools use the same copy when run with .venv/bin/python.
    assert rel.mpremote() == [sys.executable, "-m", "mpremote"]


def test_mpremote_falls_back_to_path_then_none(monkeypatch):
    monkeypatch.setattr(rel.importlib.util, "find_spec", lambda _name: None)
    monkeypatch.setattr(rel.shutil, "which", lambda _name: "/usr/local/bin/mpremote")
    assert rel.mpremote() == ["/usr/local/bin/mpremote"]
    monkeypatch.setattr(rel.shutil, "which", lambda _name: None)
    assert rel.mpremote() is None


# --- badge_info ----------------------------------------------------------------

def test_parse_info_reads_the_marked_line():
    out = 'MicroPython chatter\nBADGE_INFO {"model": "badger"}\n'
    assert badge_info.parse_info(out) == {"model": "badger"}


def test_device_snippet_is_valid_micropython_syntax(tmp_path):
    assert_micropython_syntax(badge_info.DEVICE_SNIPPET, tmp_path)


def test_device_snippet_reads_the_dice_rollers_saved_record():
    assert '"/state/dice_roller.json"' in badge_info.DEVICE_SNIPPET


def summary(apps, version="v1.26.0 on 2025-11-20", release=None):
    info = {"version": version, "apps": apps, "state": None, "free_kb": 900,
            "model": "badger", "model_source": "badge.model", "machine": "x", "release": "1.26"}
    return badge_info.summarise("/dev/x", info, release)


def test_badge_info_reports_whether_the_dice_roller_is_installed(capsys):
    assert summary(["menu", "dice_roller"])["app_installed"] is True
    assert summary(["menu"])["app_installed"] is False
    assert summary(None)["app_installed"] is None
    badge_info.report(summary(["menu", "dice_roller"]), "offline")
    out = capsys.readouterr().out
    assert "Dice Roller: installed" in out
    assert re.search(r"^Latest: +offline$", out, re.MULTILINE)


def test_badge_info_flags_older_firmware(capsys):
    release = {"tag_name": "v3.1.1", "published_at": "2026-09-23T12:11:22Z"}
    info = summary(["menu"], release=release)
    assert info["firmware_status"] == "older"
    badge_info.report(info, None)
    assert "OLDER: built 2025-11-20" in capsys.readouterr().out


def test_badge_info_restarts_the_badge_after_reading_it():
    # mpremote stops the running program; without a reset the badge sits
    # on a frozen screen until someone presses RESET.
    cmd = badge_info.mpremote_command("/dev/cu.usbmodem1101")
    assert cmd[:4] == ["mpremote", "connect", "/dev/cu.usbmodem1101", "exec"]
    assert cmd[-1] == "reset"
    assert "reset" not in badge_info.mpremote_command("/dev/x", restart=False)
    venv = badge_info.mpremote_command("/dev/x", mpremote=["python", "-m", "mpremote"])
    assert venv[:4] == ["python", "-m", "mpremote", "connect"]


# --- waiting for the user's button press ---------------------------------------

class FakeClock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_wait_for_returns_as_soon_as_something_appears():
    clock, polls = FakeClock(), []

    def find():
        polls.append(clock.now)
        return ["/Volumes/BADGER"] if clock.now >= 3 else []

    found = rel.wait_for(find, timeout=60, interval=1, clock=clock.time, sleep=clock.sleep)
    assert found == ["/Volumes/BADGER"]
    assert polls == [0, 1, 2, 3]


def test_wait_for_gives_up_after_the_timeout():
    clock = FakeClock()
    found = rel.wait_for(list, timeout=10, interval=1, clock=clock.time, sleep=clock.sleep)
    assert found == []
    assert clock.now == 10


def test_wait_for_with_no_timeout_looks_once():
    clock = FakeClock()
    assert rel.wait_for(list, timeout=0, clock=clock.time, sleep=clock.sleep) == []
    assert clock.now == 0


# --- flash_firmware: knowing when the flash has finished ----------------------

BADGER_DEVS = "/dev/cu.usbmodem201401 43a7 2e8a:1100 Pimoroni Pimoroni Badger 2350 MicroPython\n"


def test_flash_is_confirmed_when_the_badge_is_back_in_normal_mode():
    answers = iter(["", "", BADGER_DEVS])
    port = flash_firmware.wait_for_restart(
        "badger", timeout=10, list_devs=lambda: next(answers), interval=0)
    assert port == "/dev/cu.usbmodem201401"


def test_flash_confirmation_ignores_other_badges_and_gives_up():
    tufty_only = DEVS  # a Tufty and a Particle board, but no Badger
    port = flash_firmware.wait_for_restart(
        "badger", timeout=0, list_devs=lambda: tufty_only, interval=0)
    assert port is None


def test_boot_drives_need_info_uf2(tmp_path, monkeypatch):
    real, fake = tmp_path / "RP2350", tmp_path / "other" / "RP2350"
    real.mkdir()
    (real / "INFO_UF2.TXT").write_text("UF2 Bootloader")
    fake.mkdir(parents=True)
    monkeypatch.setattr(rel, "mount_bases", lambda: [tmp_path, tmp_path / "other"])
    assert flash_firmware.find_boot_drives() == [real]
