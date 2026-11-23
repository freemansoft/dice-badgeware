#!/usr/bin/env python3
"""Check the Dice Roller on a badge after an install, from the badge's side.

    .venv/bin/python tools/badge_check.py files
    .venv/bin/python tools/badge_check.py files --wait 60

files: lists /system/apps/dice_roller on the badge itself and compares it
with apps/dice_roller here (names and sizes), so it shows what the badge
really holds. Run it after the eject: until then the computer may still
be holding writes, so the mounted drive can look right when the badge
isn't (files cut short show up later as a SyntaxError when the app
starts).

The badge must be in normal mode (menu or an app on screen). The check
stops the running app and ends with machine.reset(): a Badger reopens
the app it was showing, a Tufty opens the menu.

Needs mpremote (in requirements-dev.txt; .venv/bin/python finds the
pinned copy). Standard library otherwise.

(Adapted from freemansoft/MoodBadger2350.)
"""

import argparse
import json
import sys
from pathlib import Path

import badge_info
from install import APP, SRC, _app_files

TAG = "BADGE_CHECK "

# Runs on the badge: every file under the app folder, with its size.
FILES_SNIPPET = r"""
import json, os
root = "/system/apps/APP"
files = {}
def walk(path):
    for name in os.listdir(path):
        full = path + "/" + name
        st = os.stat(full)
        if st[0] & 0x4000:
            walk(full)
        else:
            files[full[len(root) + 1:]] = st[6]
try:
    walk(root)
    print("TAG" + json.dumps({"files": files}))
except OSError:
    print("TAG" + json.dumps({"files": None}))
""".replace("APP", APP).replace("TAG", TAG)


def mpremote_command(port, snippet, mpremote=("mpremote",)):
    """Run ``snippet`` on the badge, then restart it (machine.reset()) so it
    isn't left frozen at the REPL."""
    return [*mpremote, "connect", port, "exec", snippet, "reset"]


def parse_tagged(output):
    for line in output.splitlines():
        if line.startswith(TAG):
            return json.loads(line[len(TAG):])
    raise ValueError("no {}line in:\n{}".format(TAG, output))


def local_files(folder):
    """{relative path: size} of the files install.py copies from ``folder``."""
    return {name: (Path(folder) / name).stat().st_size for name in _app_files(Path(folder))}


def compare_files(local, badge):
    """Problems found comparing {path: size} here with the badge's; {} if none."""
    junk = sorted(n for n in badge if n.split("/")[-1].startswith("._") or "__pycache__" in n)
    problems = {
        "missing": sorted(n for n in local if n not in badge),
        "different size": sorted(n for n in local if n in badge and badge[n] != local[n]),
        "not in the app": sorted(n for n in badge if n not in local and n not in junk),
        "macOS junk": junk,
    }
    return {k: v for k, v in problems.items() if v}


def read(port, snippet):
    result = badge_info.run(mpremote_command(port, snippet, badge_info.need_mpremote()))
    if result.returncode != 0:
        sys.exit("mpremote failed:\n" + (result.stderr or result.stdout))
    return parse_tagged(result.stdout)


def check_files(port, src=SRC):
    badge = read(port, FILES_SNIPPET)["files"]
    if badge is None:
        sys.exit("The Dice Roller isn't installed on the badge (no /system/apps/{}).".format(APP))
    local = local_files(src)
    problems = compare_files(local, badge)
    print("{} files on the badge, {} in apps/{}".format(len(badge), len(local), APP))
    if not problems:
        print("The badge's copy matches.")
        return
    for kind, names in problems.items():
        print("{}: {}".format(kind, ", ".join(names)))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("check", choices=("files",))
    parser.add_argument("--port", help="the badge's serial port (default: find it)")
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                        help="wait this long for the badge to appear (default: don't wait)")
    args = parser.parse_args()

    badge_info.need_mpremote()
    port = badge_info.choose_port(args.port, args.wait)
    check_files(port)


if __name__ == "__main__":
    main()
