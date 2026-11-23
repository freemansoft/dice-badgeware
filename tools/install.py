#!/usr/bin/env python3
"""Copy the Dice Roller app onto a Badgeware badge in USB disk mode.

1. Double-tap RESET on the back of the badge. It mounts as a USB drive
   (TUFTY on a Tufty 2350, BADGER on a Badger 2350).
2. Run:  python3 tools/install.py            (finds the drive)
     or  python3 tools/install.py --dest /Volumes/TUFTY
     or  python tools\\install.py --dest E:\\
3. On macOS and Linux the script ejects the drive itself and the badge
   restarts into the menu. On Windows, eject it from the taskbar.

Only apps/dice_roller is replaced; other apps and the saved dice (in
/state, on the badge's internal storage, not on this drive) stay. The
install is hardened:

- The new copy is built in a folder at the drive's root (.dice_roller.new,
  outside apps/, so the menu never lists a half-copied app), checked byte
  for byte against apps/dice_roller, then swapped in with renames.
- If the copy is interrupted (a RESET, a pulled cable, a full drive) or
  the check fails, the old app stays in place and working: run this
  again. Leftovers of an interrupted run are cleared next time.
- The "._" files macOS writes beside every file on the drive are removed.

The check reads back through the computer's cache, so it can't tell
whether every write has reached the badge. Never press RESET or unplug
the badge before the drive is ejected: the computer writes to the drive
lazily, and files cut short on the badge show up later as a SyntaxError
when the app starts.

Adapted from claude-buddy-badgeware's tools/install.py (the "._"
cleanup too) and MoodBadger2350's (the staged, checked copy).

Standard library only; works on macOS, Windows and Linux.
"""

import argparse
import filecmp
import os
import shutil
import string
import subprocess
import sys
from pathlib import Path

APP = "dice_roller"
LABELS = ("BADGER", "TUFTY", "BADGER2350", "TUFTY2350")
SRC = Path(__file__).resolve().parent.parent / "apps" / APP
JUNK = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "._*")


def _looks_like_badge(root):
    return (root / "apps").is_dir() and (root / "main.py").is_file()


def _windows_label(drive):
    import ctypes

    buf = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(drive), buf, len(buf), None, None, None, None, 0
    )
    return buf.value if ok else ""


def _ignore_missing(_func, _path, exc):
    """rmtree error handler. On macOS the badge's FAT drive holds "._"
    companion files that vanish along with their main file, so
    deleting one that's already gone isn't an error."""
    if not isinstance(exc, FileNotFoundError):
        raise exc


def _remove_tree(path):
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_ignore_missing)  # onerror is deprecated from 3.12
    else:
        shutil.rmtree(path, onerror=lambda func, p, info: _ignore_missing(func, p, info[1]))


def remove_apple_double(target):
    """Delete the "._" files macOS writes next to each copied file, and
    the one beside the target folder itself.

    The badge's drive is FAT, which can't hold extended attributes, so
    macOS stores them (com.apple.provenance at least, which it stamps on
    every new file, so copying without metadata doesn't avoid it) in a
    "._<name>" companion file. The badge never uses them. Returns how
    many were removed; on other OSes there are none.
    """
    target = Path(target)
    removed = 0
    partner = target.parent / ("._" + target.name)
    for path in [partner, *sorted(target.rglob("._*"))]:
        if path.is_file():
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            removed += 1
    return removed


def _app_files(folder):
    """Relative paths of the files the install copies (JUNK left out)."""
    files = []
    for path in sorted(Path(folder).rglob("*")):
        parts = path.relative_to(folder).parts
        if path.is_file() and not any(
            part == "__pycache__" or part.startswith(".") or part.endswith(".pyc") for part in parts
        ):
            files.append(path.relative_to(folder).as_posix())
    return files


def verify_copy(src, copy):
    """Relative paths of app files missing from ``copy`` or differing from
    ``src``, byte for byte. (Reads go through the computer's cache, so
    this catches a bad or short copy, not data still waiting to be
    written: ejecting is what makes sure of that.)"""
    return [
        name for name in _app_files(src)
        if not (Path(copy) / name).is_file() or not filecmp.cmp(Path(src) / name, Path(copy) / name, shallow=False)
    ]


def install_app(src, root):
    """Replace apps/<APP> on the drive at ``root`` with ``src``; return the
    installed folder. Raises OSError, with the old app still in place.

    The new copy is built and checked in a folder at the drive's root,
    outside apps/ (so the menu never lists a half-copied app), then
    swapped in with renames. An interrupted copy (a RESET, a pulled
    cable, a full drive) or a failed check leaves the old app working;
    leftovers are cleared on the next run. Adapted from MoodBadger2350's
    tools/install.py.
    """
    target = root / "apps" / APP
    staging = root / f".{APP}.new"
    old = root / f".{APP}.old"
    for leftover in (staging, old):
        if leftover.exists():
            _remove_tree(leftover)

    shutil.copytree(src, staging, ignore=JUNK, copy_function=shutil.copyfile)
    remove_apple_double(staging)
    bad = verify_copy(src, staging)
    if bad:
        raise OSError("the copy didn't match for " + ", ".join(bad))

    if target.exists():
        target.rename(old)
    try:
        staging.rename(target)
    except OSError:
        if old.exists():
            old.rename(target)  # put the old app back
        raise
    if old.exists():
        _remove_tree(old)
    remove_apple_double(target)
    return target


def _run(cmd, run):
    """Run ``cmd``; return its stdout, or None (printing why) on failure."""
    try:
        result = run(cmd, capture_output=True, text=True)
    except OSError as e:  # the command isn't installed
        print(f"{cmd[0]}: {e}", file=sys.stderr)
        return None
    if result.returncode != 0:
        print((result.stderr or result.stdout).strip(), file=sys.stderr)
        return None
    return result.stdout


def eject(root, run=subprocess.run, platform=sys.platform):
    """Eject the badge drive so every write reaches it before it restarts.

    Copying returns once the data is in the computer's cache, not on the
    badge. A RESET or unplug in that gap leaves truncated files (seen on
    a Badger: several files cut to 4096 bytes, one FAT cluster), which
    the app reports as a SyntaxError. Ejecting flushes everything first.
    A badge put in drive mode by a double-tap of RESET then restarts into
    the menu by itself; one put there over mpremote (import _msc) needs a
    press of RESET, which is safe once ejected.

    Returns True if the drive was ejected, False if the user must eject
    it (a command failed, or an OS this doesn't handle). Windows isn't
    handled; main() tells the user to eject from the taskbar instead.
    """
    if platform == "darwin":
        return _run(["diskutil", "eject", str(root)], run) is not None
    if platform.startswith("linux"):
        # Find the block device while it's still mounted, unmount it,
        # then power it off: power-off is the eject the badge sees.
        # udisksctl works without root for a desktop automount.
        device = _run(["findmnt", "-no", "SOURCE", str(root)], run)
        if not device or not device.strip():
            return False
        device = device.strip()
        return (
            _run(["udisksctl", "unmount", "-b", device], run) is not None
            and _run(["udisksctl", "power-off", "-b", device], run) is not None
        )
    return False


def find_badge():
    candidates = []
    if os.name == "nt":
        for letter in string.ascii_uppercase[3:]:
            drive = f"{letter}:\\"
            if os.path.exists(drive) and _windows_label(drive).upper() in LABELS:
                candidates.append(Path(drive))
    else:
        # Labels vary in case and form (TUFTY, Tufty2350), and
        # Linux paths are case-sensitive, so compare names upper-cased.
        if sys.platform == "darwin":
            bases = [Path("/Volumes")]
        else:
            user = os.environ.get("USER", "")
            bases = [Path("/media") / user, Path("/run/media") / user, Path("/mnt")]
        for base in bases:
            if base.is_dir():
                candidates += [c for c in base.iterdir() if c.name.upper() in LABELS]
    return [c for c in candidates if c.is_dir() and _looks_like_badge(c)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", help="root of the badge's USB drive (contains apps/ and main.py)")
    parser.add_argument("--no-eject", action="store_true", help="leave the drive mounted (eject it yourself)")
    args = parser.parse_args()

    if args.dest:
        root = Path(args.dest)
        if not _looks_like_badge(root):
            sys.exit(f"{root} doesn't look like a Badgeware drive (no apps/ or main.py)")
    else:
        found = find_badge()
        if not found:
            sys.exit("No badge drive found. Double-tap RESET on the badge, or pass --dest.")
        if len(found) > 1:
            sys.exit("Several badge drives found ({}); pass --dest.".format(", ".join(map(str, found))))
        root = found[0]

    print(f"Copying to {root}. Don't press any buttons until it has ejected.", flush=True)
    try:
        target = install_app(SRC, root)
    except OSError as e:
        sys.exit(f"The install failed ({e}).\nThe old Dice Roller, if there was one, is still in place. "
                 "If the drive is still mounted, run this again.")
    print(f"Installed and checked {len(_app_files(SRC))} files in {target}")
    if args.no_eject or os.name == "nt":
        print("Eject the drive before pressing RESET or unplugging, or the copied")
        print("files may be cut short. The badge then restarts into the menu.")
    elif eject(root):
        print(f"Ejected {root}. The badge restarts into the menu; if it doesn't,")
        print("press RESET (safe now).")
    else:
        print(f"Couldn't eject {root}. Eject it yourself before pressing RESET or")
        print("unplugging, or the copied files may be cut short.")
        sys.exit(1)


if __name__ == "__main__":
    main()
