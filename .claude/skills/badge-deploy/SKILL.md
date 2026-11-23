---
name: badge-deploy
description: Use when the Dice Roller has to go onto a real Tufty 2350 or Badger 2350 - the user says a badge is plugged in, mounted, in disk mode or "ready for code", asks to install, update or try a branch on the badge, says the badge still shows an old version, or a finished branch is about to be pushed (the user tests on hardware first).
---

# Deploying the Dice Roller to a badge

## Overview

The user tests every branch on their real badges before it is pushed.
Installing means: put **the committed code** of the branch on the badge,
with `tools/install.py`, after the project checks pass, then tell the
user exactly which commit is on the badge and what to look at.

`tools/install.py` is hardened (see its docstring): it builds the copy
in `.dice_roller.new` at the drive's root, checks every file byte for
byte, swaps it into `apps/dice_roller`, removes macOS `._` files and
ejects. A failed or interrupted install leaves the old app working. The
saved dice live in `/state` on the badge's internal storage, not on the
drive, so an install keeps them.

## Steps

1. **Checks must pass on what you will install.** Commit your own work
   first, so the checks cover exactly the commit that goes on the badge.
   Stop and report if any fails; never install a red tree.

   ```bash
   .venv/bin/pytest -q && .venv/bin/ruff check . \
     && find apps/dice_roller -name '*.py' -print0 | xargs -0 -n1 .venv/bin/python -m mpy_cross -o /dev/null
   ```

   Don't pipe pytest into `tail` or `grep` without `set -o pipefail`: the
   pipe hides a failure. If the user has uncommitted edits of their own,
   the checks ran on those too: say so in the report.

2. **Export the commit, not the working tree.** `install.py` copies the
   `apps/dice_roller` next to it, so run an exported copy:

   ```bash
   EXPORT="$SCRATCHPAD/export-$(git rev-parse --short HEAD)"   # the session's scratchpad directory
   rm -rf "$EXPORT" && mkdir -p "$EXPORT"
   git archive HEAD apps/dice_roller tools | tar -x -C "$EXPORT"
   ```

   If `git status --short` shows changes under `apps/dice_roller` or
   `tools/`, say they are not being installed. Install the working tree only if the
   user asks for it, and say so in the report.

3. **Find the drive.** `ls /Volumes` must show `BADGER` or `TUFTY`
   (other names, like a leftover test image, aren't badges). If it's
   missing, ask the user to double-tap RESET (disk mode) and tell you
   when the drive appears, then end your turn. Don't start a background
   waiter; if one of yours is still running, stop it first (TaskStop,
   with the task id its start reported). Two installers on one drive
   race and corrupt the copy.

   Install to the badge the user named. If only the other one is
   mounted, ask. If both are, install one at a time, each with its own
   `--dest`.

4. **Install in the foreground**, with the drive named:

   ```bash
   python3 "$EXPORT/tools/install.py" --dest /Volumes/BADGER   # or TUFTY
   ```

   It prints "Installed and checked N files" and "Ejected". On "The
   install failed": run it again (the old app is still there); if it
   keeps failing, suspect a full drive or a flaky cable. On "Couldn't
   eject": tell the user to eject in Finder before touching the badge.

5. **Report**, in this order:
   - the branch and short commit now on the badge (and that uncommitted
     edits were or weren't included);
   - it's safe to unplug or press RESET now that it has ejected; the
     badge restarts into the menu by itself (press RESET once if the
     disk-mode screen is still up after about 10 s);
   - a short list of what to look at on the badge **for this change**
     (screens, buttons, the look), plus anything only hardware shows:
     e-ink refresh, sleep and wake on battery, colours.

   Then wait. Push or open a PR only when the user says so, after they
   have tried it.

## Quick reference

| Situation                           | Do                                                                |
| ----------------------------------- | ----------------------------------------------------------------- |
| Uncommitted app edits               | Install the commit; say the edits aren't on the badge             |
| No `BADGER` / `TUFTY` in `/Volumes` | Ask for a double-tap of RESET; end the turn                       |
| Install failed                      | Run again; the old app still works                                |
| Couldn't eject                      | User ejects in Finder before any button                           |
| Both badges                         | Install once per badge; same folder, the app checks `badge.model` |
| Change only affects one badge       | Say the other doesn't need it                                     |

## Common mistakes

- Installing from the working tree, so the badge runs code that isn't
  in any commit.
- Starting a background "wait for the drive" install and later a second
  one: they race.
- Telling the user it's safe before "Ejected" is printed.
- Reporting "installed" without the commit.
- Pushing straight after installing, before the user has tried it.
