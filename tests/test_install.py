import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import install

APP_SRC = Path(__file__).resolve().parent.parent / "apps" / "dice_roller"


def test_installs_app_onto_drive(tmp_path, monkeypatch):
    (tmp_path / "apps").mkdir()
    (tmp_path / "main.py").write_text("")
    (APP_SRC / "__pycache__").mkdir(exist_ok=True)
    monkeypatch.setattr(sys, "argv", ["install.py", "--dest", str(tmp_path), "--no-eject"])
    assert install.main() in (0, None)
    dest = tmp_path / "apps" / "dice_roller"
    for name in [p.name for p in APP_SRC.glob("*.py")] + ["icon.png"]:
        assert (dest / name).is_file(), name
    assert not (dest / "__pycache__").exists()
