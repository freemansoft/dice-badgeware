import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "dice_roller"))


def assert_micropython_syntax(source, tmp_path):
    """Compile ``source`` with mpy-cross, which rejects syntax that
    CPython's compile() accepts but MicroPython doesn't."""
    path = tmp_path / "snippet.py"
    path.write_text(source)
    done = subprocess.run([sys.executable, "-m", "mpy_cross", "-o", os.devnull, str(path)],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
