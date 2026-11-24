"""The prettier version lives in one place, .prettier-version, which the
pre-commit hook and CI read. Any other file that writes the version out
would drift from it."""

import re
import subprocess

from conftest import ROOT

VERSION_FILE = ROOT / ".prettier-version"
PINNED = re.compile(r"prettier@\d")


def repo_files():
    """Tracked files, plus new ones not yet added (but not ignored ones).
    Submodules (vendor/) are listed as directories and skipped."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return [ROOT / name for name in out.split("\0") if name and (ROOT / name).is_file()]


def test_version_file_holds_just_a_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+\n?", VERSION_FILE.read_text())


def test_no_other_file_hard_codes_the_prettier_version():
    offenders = []
    for path in repo_files():
        if path == VERSION_FILE:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue  # binary files (the simulator's wasm, the icon)
        if PINNED.search(text):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_hook_and_ci_read_the_version_file():
    for path in (".githooks/pre-commit", ".github/workflows/ci.yml"):
        assert ".prettier-version" in (ROOT / path).read_text(), path
