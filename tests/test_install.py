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


def test_remove_apple_double_removes_only_dot_underscore_files(tmp_path):
    (tmp_path / "game").mkdir()
    for name in ("__init__.py", "._init__.py", "icon.png", "._icon.png", "game/dice.py", "game/._dice.py"):
        (tmp_path / name).write_text("x")
    assert install.remove_apple_double(tmp_path) == 3
    left = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert left == ["__init__.py", "game/dice.py", "icon.png"]


def test_remove_apple_double_with_nothing_to_remove(tmp_path):
    (tmp_path / "__init__.py").write_text("x")
    assert install.remove_apple_double(tmp_path) == 0


def test_install_removes_the_apple_double_files_macos_writes(tmp_path, monkeypatch):
    # macOS writes a "._" companion beside each file it copies to the FAT
    # drive, on the drive itself, so the copy's ignore list can't stop it
    copytree = install.shutil.copytree

    def copy_like_macos(src, dst, *args, **kwargs):  # also called for each subfolder
        copytree(src, dst, *args, **kwargs)
        for path in list(Path(dst).iterdir()):
            if not path.name.startswith("._"):
                (path.parent / ("._" + path.name)).write_text("xattr")
        return dst

    monkeypatch.setattr(install.shutil, "copytree", copy_like_macos)
    (tmp_path / "apps").mkdir()
    (tmp_path / "main.py").write_text("")
    monkeypatch.setattr(sys, "argv", ["install.py", "--dest", str(tmp_path), "--no-eject"])
    install.main()
    dest = tmp_path / "apps" / "dice_roller"
    assert (dest / "__init__.py").exists()
    assert not list(dest.rglob("._*"))


def badge_with_old_app(root):
    """A badge drive holding a working older copy of the app."""
    (root / "main.py").write_text("")
    old = root / "apps" / "dice_roller"
    old.mkdir(parents=True)
    (old / "__init__.py").write_text("old app")
    return old


def run_install(root, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["install.py", "--dest", str(root), "--no-eject"])
    return install.main()


def test_a_bad_copy_is_caught_and_the_old_app_kept(tmp_path, monkeypatch):
    old = badge_with_old_app(tmp_path)
    copyfile = install.shutil.copyfile

    def short_copy(src, dst, **kwargs):  # a write that came out short
        copyfile(src, dst, **kwargs)
        if Path(src).name == "dice.py":
            Path(dst).write_bytes(Path(dst).read_bytes()[:10])
        return dst

    monkeypatch.setattr(install.shutil, "copyfile", short_copy)
    with pytest.raises(SystemExit) as stopped:
        run_install(tmp_path, monkeypatch)
    assert stopped.value.code not in (0, None)
    assert "game/dice.py" in str(stopped.value) and "still" in str(stopped.value)
    assert (old / "__init__.py").read_text() == "old app"


def test_an_interrupted_copy_leaves_the_old_app_working(tmp_path, monkeypatch):
    old = badge_with_old_app(tmp_path)
    copyfile = install.shutil.copyfile

    def drive_gone(src, dst, **kwargs):
        if Path(src).name == "badger.py":
            raise OSError("drive removed")
        return copyfile(src, dst, **kwargs)

    monkeypatch.setattr(install.shutil, "copyfile", drive_gone)
    with pytest.raises(SystemExit):
        run_install(tmp_path, monkeypatch)
    assert sorted(p.name for p in old.iterdir()) == ["__init__.py"]
    assert (old / "__init__.py").read_text() == "old app"


def test_the_old_app_comes_back_if_the_swap_fails(tmp_path, monkeypatch):
    old = badge_with_old_app(tmp_path)
    rename = Path.rename

    def failing_rename(self, target):
        if self.name == ".dice_roller.new":
            raise OSError("rename failed")
        return rename(self, target)

    monkeypatch.setattr(Path, "rename", failing_rename)
    with pytest.raises(SystemExit):
        run_install(tmp_path, monkeypatch)
    assert (old / "__init__.py").read_text() == "old app"


def test_leftovers_of_an_interrupted_run_are_cleared(tmp_path, monkeypatch):
    badge_with_old_app(tmp_path)
    for leftover in (".dice_roller.new", ".dice_roller.old"):
        (tmp_path / leftover / "game").mkdir(parents=True)
        (tmp_path / leftover / "game" / "half.py").write_text("x")
    run_install(tmp_path, monkeypatch)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["apps", "main.py"]
    assert app_files(tmp_path / "apps" / "dice_roller") == app_files(APP_SRC)


def test_remove_apple_double_also_removes_the_folders_own_companion(tmp_path):
    app = tmp_path / "apps" / "dice_roller"
    app.mkdir(parents=True)
    (app / "__init__.py").write_text("x")
    (tmp_path / "apps" / "._dice_roller").write_text("x")
    (tmp_path / "apps" / "._other_app").write_text("x")  # another app's: not ours to touch
    assert install.remove_apple_double(app) == 1
    assert sorted(p.name for p in (tmp_path / "apps").iterdir()) == ["._other_app", "dice_roller"]
