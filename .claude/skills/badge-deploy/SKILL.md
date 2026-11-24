---
name: badge-deploy
description: Use when the Dice Roller has to go onto a real Tufty 2350 or Badger 2350 - the user says a badge is plugged in, mounted, in disk mode or "ready for code", asks to install, update or try a branch on the badge, says the badge still shows an old version, or a finished branch is about to be pushed (the user tests on hardware first). Checks the badge's firmware first, installs the committed code, then checks the copy from the badge's side after the eject. For flashing firmware use badge-firmware; for which tests a change needs, badge-verify.
---

# Deploying the Dice Roller to a badge

## Overview

The user tests every branch on their real badges before it is pushed.
Installing means: put **the committed code** of the branch on the badge,
with `tools/install.py`, after the project checks pass and the badge's
firmware is checked, then check the copy from the badge's side and tell
the user exactly which commit is on the badge and what to look at.

`tools/install.py` is hardened (see its docstring): it builds the copy
in `.dice_roller.new` at the drive's root, checks every file byte for
byte, swaps it into `apps/dice_roller`, removes macOS `._` files and
ejects. A failed or interrupted install leaves the old app working. The
saved dice live in `/state` on the badge's internal storage, not on the
drive, so an install keeps them.

Badger vs Tufty differences (what each restart opens, sleep, the
e-ink): see the `badgeware-platforms` skill. Which test layers a change
needs before it goes on a badge: the `badge-verify` skill.

The badge tools that talk to the badge over USB serial
(`badge_info.py`, `badge_check.py`) need `mpremote`, so run them with
`.venv/bin/python`, which has the pinned copy. Each one stops the
running app and ends with `machine.reset()`: a Badger reopens the app
it was showing, a Tufty opens the menu.

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

3. **Check the badge's firmware first.** The app is built and tested
   against Badgeware v3.1.1 (the `vendor/` submodules). If the badge is
   on USB in normal mode (menu or an app on screen), run:

   ```bash
   .venv/bin/python tools/badge_info.py
   ```

   - **"Firmware: OLDER"** (or no build date): stop. Tell the user the
     badge's firmware is older than Pimoroni's latest release and offer
     to update it with the `badge-firmware` skill (`--firmware-only`
     keeps the apps and saved dice). Install only after that, or if
     the user says to go ahead on the old firmware.
   - **Looks current** (or newer): note the model and carry on. The
     badge restarts when the tool finishes.
   - **Model is neither `tufty` nor `badger`:** there's no display for
     it yet (the app shows "not supported"). Say so before installing.
   - **No badge found:** it may be asleep (press RESET once), on a
     charge-only cable, or already in disk mode.

   If the badge is **already in disk mode** (`BADGER` or `TUFTY` in
   `/Volumes`), the firmware can't be read. Say so, and ask the user
   whether it was checked recently; if not, tell them how: eject the
   drive, press RESET once, and you'll run `badge_info.py`. Carry on
   only if they confirm it's current or tell you to install anyway.

4. **Find the drive.** `ls /Volumes` must show `BADGER` or `TUFTY`
   (other names, like a leftover test image, aren't badges). If it's
   missing, ask the user to double-tap RESET (disk mode) and tell you
   when the drive appears, then end your turn. Don't start a background
   waiter; if one of yours is still running, stop it first (TaskStop,
   with the task id its start reported). Two installers on one drive
   race and corrupt the copy.

   Install to the badge the user named. If only the other one is
   mounted, ask. If both are, install one at a time, each with its own
   `--dest`.

5. **Install in the foreground**, with the drive named:

   ```bash
   python3 "$EXPORT/tools/install.py" --dest /Volumes/BADGER   # or TUFTY
   ```

   It prints "Installed and checked N files" and "Ejected". On "The
   install failed": run it again (the old app is still there); if it
   keeps failing, suspect a full drive or a flaky cable. On "Couldn't
   eject": tell the user to eject in Finder before touching the badge.

6. **Check the copy from the badge's side**, after "Ejected" and once
   the badge has restarted into the menu:

   ```bash
   .venv/bin/python "$EXPORT/tools/badge_check.py" files --wait 30
   ```

   Run the exported copy, so it compares with the commit you installed.
   It lists `/system/apps/dice_roller` on the badge and compares names
   and sizes with `apps/dice_roller`. Expect "The badge's copy
   matches." Any "missing" or "different size" line means the copy
   didn't reach the badge whole (files cut short show up as a
   SyntaxError when the app starts): install again. "macOS junk" (`._`
   or `__pycache__` files) also means install again. Don't check by
   reading the mounted drive instead: the computer holds writes in its
   cache until the eject, so the drive can look right when the badge
   isn't. If the badge isn't on USB serial (no data cable, asleep),
   say the check was skipped.

7. **Report**, in this order:
   - the branch and short commit now on the badge (and that uncommitted
     edits were or weren't included);
   - the firmware check (model, "looks current" or what the user
     decided) and the badge-side file check;
   - it's safe to unplug or press RESET now that it has ejected; the
     badge restarts into the menu by itself (press RESET once if the
     disk-mode screen is still up after about 10 s);
   - a short list of what to look at on the badge **for this change**
     (screens, buttons, the look), plus anything only hardware shows:
     e-ink refresh, sleep and wake on battery, colours. The
     `badge-verify` skill has a hand checklist for each badge.

   Then wait. Push or open a PR only when the user says so, after they
   have tried it.

## Quick reference

| Situation                           | Do                                                                |
| ----------------------------------- | ----------------------------------------------------------------- |
| `badge_info.py` says OLDER          | Stop; offer the update with `badge-firmware`                      |
| Already in disk mode                | Can't read firmware: ask the user, or eject, RESET and check      |
| `badge_check.py` finds a problem    | Install again; the old files are on the badge                     |
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
- Skipping the firmware check because the drive is already mounted,
  without telling the user.
- Checking the copy on the mounted drive instead of with
  `badge_check.py` after the eject.
- Reporting "installed" without the commit.
- Pushing straight after installing, before the user has tried it.
