import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import install

APP_SRC = Path(__file__).resolve().parent.parent / "apps" / "dice_roller"


def test_installs_app_onto_drive_replacing_the_old_copy(tmp_path, monkeypatch):
    dest = tmp_path / "apps" / "dice_roller"
    dest.mkdir(parents=True)
    (dest / "removed_since.py").write_text("")
    (dest / "dice.py").write_text("old")
    (tmp_path / "main.py").write_text("")
    (APP_SRC / "__pycache__").mkdir(exist_ok=True)
    monkeypatch.setattr(sys, "argv", ["install.py", "--dest", str(tmp_path), "--no-eject"])
    assert install.main() in (0, None)
    for name in [p.name for p in APP_SRC.glob("*.py")] + ["icon.png"]:
        assert (dest / name).read_bytes() == (APP_SRC / name).read_bytes(), name
    assert not (dest / "__pycache__").exists()
    assert not (dest / "removed_since.py").exists()


def test_refuses_a_folder_that_is_not_a_badge_drive(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["install.py", "--dest", str(tmp_path), "--no-eject"])
    with pytest.raises(SystemExit) as stopped:
        install.main()
    assert stopped.value.code not in (0, None)
    assert list(tmp_path.iterdir()) == []
