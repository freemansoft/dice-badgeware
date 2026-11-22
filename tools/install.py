#!/usr/bin/env python3
"""Copy the Dice Roller app onto a Badgeware badge in USB disk mode.

Ported from claude-buddy-badgeware's tools/install.py.

1. Double-tap RESET on the back of the badge. It mounts as a USB drive
   (TUFTY on a Tufty 2350).
2. Run:  python3 tools/install.py            (finds the drive)
     or  python3 tools/install.py --dest /Volumes/TUFTY
     or  python tools\\install.py --dest E:\\
3. On macOS and Linux the script ejects the drive itself and the badge
   restarts into the menu. On Windows, eject it from the taskbar.

Never press RESET or unplug the badge before the drive is ejected: the
computer writes to the drive lazily, and files cut short on the badge
show up later as a SyntaxError when the app starts.

Standard library only; works on macOS, Windows and Linux.
"""

import argparse
import os
import shutil
import string
import subprocess
import sys
from pathlib import Path

APP = "dice_roller"
LABELS = ("BADGER", "TUFTY", "BADGER2350", "TUFTY2350")
SRC = Path(__file__).resolve().parent.parent / "apps" / APP


def _looks_like_badge(root):
    return (root / "apps").is_dir() and (root / "main.py").is_file()


def _windows_label(drive):
    import ctypes

    buf = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(drive), buf, len(buf), None, None, None, None, 0
    )
    return buf.value if ok else ""


def _ignore_missing(_func, _path, exc_info):
    """rmtree error handler. On macOS the badge's FAT drive holds "._"
    companion files that vanish along with their main file, so
    deleting one that's already gone isn't an error."""
    if not issubclass(exc_info[0], FileNotFoundError):
        raise exc_info[1]


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

    target = root / "apps" / APP
    if target.exists():
        shutil.rmtree(target, onerror=_ignore_missing)
    shutil.copytree(SRC, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "._*"))
    print("Installed to", target)
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
