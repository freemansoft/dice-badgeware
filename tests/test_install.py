import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import install

APP_SRC = Path(__file__).resolve().parent.parent / "apps" / "dice_roller"


def app_files(root):
    """Every file under root that belongs on the badge, by relative path."""
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


def test_installs_app_onto_drive_replacing_the_old_copy(tmp_path, monkeypatch):
    dest = tmp_path / "apps" / "dice_roller"
    (dest / "game").mkdir(parents=True)
    (dest / "removed_since.py").write_text("")
    (dest / "game" / "dice.py").write_text("old")
    (tmp_path / "main.py").write_text("")
    (APP_SRC / "game" / "__pycache__").mkdir(exist_ok=True)  # git-ignored
    monkeypatch.setattr(sys, "argv", ["install.py", "--dest", str(tmp_path), "--no-eject"])
    assert install.main() in (0, None)
    expected = app_files(APP_SRC)
    assert {"__init__.py", "icon.png", "game/dice.py", "saving/store.py", "devices/badger.py"} <= expected.keys()
    assert app_files(dest) == expected  # every file, sub-packages included, and nothing stale
    assert not list(dest.rglob("__pycache__"))


def test_refuses_a_folder_that_is_not_a_badge_drive(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["install.py", "--dest", str(tmp_path), "--no-eject"])
    with pytest.raises(SystemExit) as stopped:
        install.main()
    assert stopped.value.code not in (0, None)
    assert list(tmp_path.iterdir()) == []


def fake_run(results):
    """A subprocess.run stand-in: records each command and returns the
    (returncode, stdout) given for the command's first two words."""
    calls = []

    def run(cmd, **_kwargs):
        calls.append(cmd)
        code, out = results.get(tuple(cmd[:2]), (0, ""))
        return SimpleNamespace(returncode=code, stdout=out, stderr="failed")

    return run, calls


def test_eject_on_macos_uses_diskutil():
    run, calls = fake_run({})
    assert install.eject(Path("/Volumes/TUFTY"), run=run, platform="darwin") is True
    assert calls == [["diskutil", "eject", "/Volumes/TUFTY"]]


def test_eject_on_linux_unmounts_then_powers_off_the_device():
    run, calls = fake_run({("findmnt", "-no"): (0, "/dev/sdb1\n")})
    assert install.eject(Path("/media/me/BADGER"), run=run, platform="linux") is True
    assert calls == [
        ["findmnt", "-no", "SOURCE", "/media/me/BADGER"],
        ["udisksctl", "unmount", "-b", "/dev/sdb1"],
        ["udisksctl", "power-off", "-b", "/dev/sdb1"],
    ]


@pytest.mark.parametrize(("platform", "results"), [
    ("darwin", {("diskutil", "eject"): (1, "")}),
    ("linux", {("findmnt", "-no"): (1, "")}),
    ("linux", {("findmnt", "-no"): (0, "/dev/sdb1\n"), ("udisksctl", "unmount"): (1, "")}),
    ("win32", {}),
])
def test_eject_reports_failure_so_the_user_ejects(platform, results):
    run, calls = fake_run(results)
    assert install.eject(Path("/x"), run=run, platform=platform) is False
    assert not any("power-off" in cmd for cmd in calls)  # never powered off a drive still mounted
