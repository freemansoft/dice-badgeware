---
name: badge-firmware
description: Check and update the Badgeware firmware on a Tufty 2350 or Badger 2350 plugged in by USB - identify which badge is connected and what firmware it runs, compare it with Pimoroni's latest release, download the right UF2 and flash it in bootloader mode, guiding the user through the BOOT/RESET button presses. Use whenever the user wants to update, upgrade, reflash or recover badge firmware, asks which badge or firmware version is plugged in, has a new or unboxed badge, sees "System Error" or a blank/stuck badge, wonders if a Dice Roller bug is really an old firmware, badge-deploy's firmware check says OLDER, or a new pimoroni/tufty2350 or badger2350 release comes up - even if they never say "firmware". For copying only the Dice Roller onto a badge, use badge-deploy instead.
---

# Badge firmware

The Dice Roller is built and tested against Badgeware firmware
**v3.1.1**, the version pinned in `vendor/tufty2350` and
`vendor/badger2350` (and in the simulator, `sim/wasm/VERSION.json`). A
badge ships with whatever Pimoroni flashed at the factory, and an app
bug can really be an old firmware, so know the badge's model and
firmware before trusting what it does.

Most steps need the user's hands on the buttons on the back of the
badge. Start each tool with `--wait 180` in the background and end your
turn with exactly what to press and what they should see. If it timed
out, ask what the badge's screen shows. Never assume a press happened;
read the tool's result.

The tools are standard-library Python plus `mpremote`, run from the
repository root as scripts with the project's venv, which has the
pinned `mpremote` (`requirements-dev.txt`):
`tools/badge_info.py` and `tools/flash_firmware.py`, with helpers in
`tools/badgeware_release.py`. If `.venv` is missing, set it up as
`CLAUDE.md` says.

## The badge's three USB modes

| Mode       | How the user gets there              | What the computer sees                                                                                    |
| ---------- | ------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| Normal     | Press RESET once, or just plug it in | A serial port, `Pimoroni Tufty 2350 MicroPython` or `Pimoroni Badger 2350 MicroPython` in `mpremote devs` |
| Bootloader | Hold BOOT, tap RESET, let go of BOOT | A drive named `RP2350` holding `INFO_UF2.TXT`                                                             |
| Disk mode  | Double-tap RESET                     | A drive named `TUFTY` or `BADGER`                                                                         |

Buttons, with the **back of the badge facing the user**: BOOT is
towards the far left, RESET is just to the right of BOOT. On battery
the Badger sleeps after 30 s and drops off USB; plugging in USB keeps
it awake.

## Steps

### 1. Identify the badge and check its firmware

If the user says the badge is plugged in and showing the menu or an
app, just run:

```bash
.venv/bin/python tools/badge_info.py
```

Otherwise start `.venv/bin/python tools/badge_info.py --wait 180` in
the background and ask them to plug it in with a data cable and press
RESET once.

It picks the badge out of `mpremote devs` (other boards and Bluetooth
ports are ignored; with two badges it asks for `--port`) and prints the
model, MicroPython build and build date, whether the Dice Roller is
installed, the saved dice, free space, and the latest release with a
verdict.

- **The verdict compares dates, not version numbers.** The firmware
  records when it was built, not which release it is. "Looks current"
  means built within a few days of the latest release's publish date.
  Say that when you report it; don't claim an exact version.
- **The model comes from Badgeware itself**, which is what decides the
  firmware image. Don't infer it from the drive name or USB
  description. A source of `badge.model` or `badgeware.badge.MODEL` is
  fine; `os.uname().machine` is a warning sign (below).
- **It interrupts whatever was running, then restarts the badge** with
  `machine.reset()` a couple of seconds later, without a button press.
  A Badger reopens the app it was showing; a Tufty opens the menu (see
  `badgeware-platforms`). Don't run it while the user is in the middle
  of a game.
- `model_source` of `os.uname().machine` means Badgeware didn't load:
  the firmware is damaged or not Badgeware. Reflash, and suggest
  `--with-filesystem` (step 2).

If the verdict is "looks current" and the user didn't ask for a
reflash, stop here and report.

If no badge is found: it may be asleep (press RESET), in disk mode
(eject the drive), on a charge-only cable, or not Badgeware at all. A
badge that only shows "System Error" may still be reachable in normal
mode; if not, go straight to bootloader mode, which is in ROM and
always works, and ask the user which model it is.

### 2. Choose the image (the user decides)

Every release has two images, and `flash_firmware.py` refuses to guess:

- `--firmware-only` replaces only the firmware. Apps, `main.py` and the
  saved dice stay. **The right choice for a badge already in use.**
- `--with-filesystem` also resets the badge's drive to Pimoroni's
  defaults: the Dice Roller and any added apps are removed, and
  `main.py` is replaced. The saved dice live in `/state` on a separate
  internal partition and probably survive, but don't promise it. Good
  for a new badge or a damaged filesystem, because the default apps
  then match the firmware.

Explain the trade-off in a sentence or two and let the user choose.
Don't pass `--yes` (which skips the typed confirmation) unless they
have just told you to wipe it.

Before flashing a release newer than the pinned `v3.1.1`, skim its
notes for anything the Dice Roller depends on: `run()`, `badge.update()`
and `badge.mode()`, `wait_for_button_or_alarm` and sleep, buttons,
`State`, vector fonts (`font.load`, `screen.antialias`), `shape`:

```bash
gh release view -R pimoroni/tufty2350     # or pimoroni/badger2350
```

Mention anything that looks risky before flashing.

### 3. Flash

Start the flash in the background with the model from step 1; it
downloads the image first, then waits for the drive:

```bash
.venv/bin/python tools/flash_firmware.py --model tufty --firmware-only --wait 180
```

Then tell the user, step by step: back of the badge facing them,
**hold BOOT** (far left), **tap RESET**, **let go of BOOT**. The screen
does not change, but a drive named `RP2350` appears and the flash runs
by itself. Tell them in the same message **not to press anything else
until you say it's done**: nothing on screen shows the flash is in
progress, and a RESET part-way leaves a half-written firmware (the ROM
bootloader can always recover it, but it means flashing again). End
your turn there.

`--with-filesystem` normally asks for the model name to be typed, which
a background command can't receive. Only after the user has said in
the chat that wiping the badge is fine, pass `--yes` with it.

The script downloads the UF2 from `pimoroni/<model>2350` releases
(cached in the system temp folder), checks it is a complete UF2 file,
and copies it to the `RP2350` drive. The badge restarts by itself after
a few seconds. `--tag vX.Y.Z` picks a particular release;
`--download-only` fetches without flashing. Pre-releases (for example
`v4.0.0-ide.1`) are skipped by "latest"; use one only if the user asks
for it by tag.

The script decides whether the flash worked by waiting up to 30 s for
the badge to come back in normal mode, so read its last lines:

- **"Flash complete"**: tell the user it's done and safe to touch.
- **"still in bootloader mode"**: the badge didn't take the image (or
  someone pressed BOOT and RESET again). The `RP2350` drive is still
  mounted, so run the same command again with no button presses.
- **"didn't come back on USB"**: ask what the screen shows. The menu
  means it worked. Otherwise ask for one RESET press and check with
  `badge_info.py --wait 30`.

Flashing the other model's firmware doesn't brick a badge (the
bootloader is in ROM), but nothing works until the right image is on
it. That's why the model must come from step 1, not from a guess.

### 4. Confirm

Run `.venv/bin/python tools/badge_info.py --wait 60` (ask the user to
press RESET once if it doesn't appear). Expect a model source of
`badgeware.badge.MODEL` (or `badge.model`) and a "looks current"
verdict.

### 5. Afterwards

- **After `--with-filesystem`**, the Dice Roller is gone. Offer to
  reinstall it with the `badge-deploy` skill.
- **If you came here from `badge-deploy`** (its firmware check said
  OLDER), go back to it and carry on with the install.
- **If the release is newer than the pinned `v3.1.1`**, say so. Moving
  the project to it is a separate change, not part of flashing:
  `tools/update_sim.py` moves the `vendor/` submodules and the
  simulator build (README, "Updating the simulator"), then re-check the
  `badgeware-platforms` table, every "3.1.1" mention (find them with
  `grep -rn "3\.1\.1" --exclude-dir=vendor --exclude-dir=.venv --exclude-dir=sim .`),
  and run the `badge-verify` layers. Offer it; don't do it unasked.
- Report: model, firmware before and after (build dates), which image
  was flashed, and anything the user should check by hand on the badge.

## Tufty and Badger

Badger vs Tufty differences: see the `badgeware-platforms` skill. The
tools handle both: `badge_info.py` reads `badge.model`, and
`flash_firmware.py --model tufty` fetches from `pimoroni/tufty2350`,
`--model badger` from `pimoroni/badger2350`. The button procedure is
the same. Tufty releases include pre-releases such as the Badgeware IDE
preview (`v4.0.0-ide.1`); "latest" skips them.
