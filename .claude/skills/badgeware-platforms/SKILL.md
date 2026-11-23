---
name: badgeware-platforms
description: How the Badger 2350 (e-ink) and Tufty 2350 (colour LCD) differ under the same Badgeware firmware, with each difference backed by a file in vendor/badger2350 or vendor/tufty2350, and the rules the Dice Roller follows to run on both (one display module per badge in apps/dice_roller/devices, begin_frame/end_frame, app.changes refresh, sleep, the Badger's four greys). Load it whenever you write, change, review or plan Dice Roller code under apps/dice_roller (especially devices/ and __init__.py), add a badge such as the Blinky, port something between the badges, or debug something that works on one badge but not the other - even if the user only says "make it work on the Badger", "why is the Tufty screen black" or "the e-ink looks washed out".
---

# Badger 2350 vs Tufty 2350

Both badges run Pimoroni's Badgeware firmware, built from near-identical
source trees, and app code looks portable. It isn't quite: the run loop,
the screen, the start-up flow and several built-in names differ. Each
row below was read from the firmware source pinned at **v3.1.1** in the
two submodules. Read the cited file before relying on a row, and
**re-check every row against the new tag before bumping either
submodule** (`tools/update_sim.py` moves them).

(Adapted from freemansoft/MoodBadger2350.)

## The differences

|                                                                                                                   | Badger 2350                                                                                                       | Tufty 2350                                                                                                                                                                                               | Source                                                                                                                                           |
| ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Screen                                                                                                            | e-ink, keeps its image unpowered, slow refresh                                                                    | colour LCD with a backlight, `display.backlight(0..1)`                                                                                                                                                   | `vendor/tufty2350/modules/common/badgeware/__init__.py`                                                                                          |
| Resolution                                                                                                        | 264x176                                                                                                           | 160x120 (LORES, default) or 320x240 after `badge.mode(HIRES)`                                                                                                                                            | `vendor/tufty2350/modules/common/badgeware/badge.py` (`mode()`)                                                                                  |
| Default pen and clear                                                                                             | black on white                                                                                                    | white on black                                                                                                                                                                                           | `vendor/tufty2350/modules/common/badgeware/badge.py` (`Badge.__init__`)                                                                          |
| `color.white`, `color.black`                                                                                      | pure white (255, 255, 255), pure black                                                                            | an off-white (0xde, 0xee, 0xd6) and a dark navy (0x14, 0x1e, 0x28), from a Dawnbringer palette; use `color.rgb(255, 255, 255)` and `color.rgb(0, 0, 0)` for true black and white                         | pimoroni/picovector `micropython/color.cpp` (`#ifdef TUFTY`), not vendored                                                                       |
| `run(update)` loop                                                                                                | calls `update()` only; the app calls `badge.update()` to refresh                                                  | `badge.clear()` before and `display.update()` after every `update()`, every frame (~90 fps with `VSYNC`)                                                                                                 | `vendor/badger2350/modules/common/badgeware/__init__.py`, `vendor/tufty2350/modules/common/badgeware/__init__.py` (`_run.__call__`)              |
| `badge.first_update`                                                                                              | set False after the first `badge.update()`                                                                        | never set False                                                                                                                                                                                          | `vendor/badger2350/modules/common/badgeware/badge.py`                                                                                            |
| `NON_BLOCKING`                                                                                                    | defined                                                                                                           | not defined (NameError)                                                                                                                                                                                  | `vendor/badger2350/modules/common/badgeware/badge.py`                                                                                            |
| `wait_for_button_or_alarm`                                                                                        | defined; deep-sleeps after its timeout on battery                                                                 | not defined                                                                                                                                                                                              | `vendor/badger2350/modules/common/badgeware/__init__.py`                                                                                         |
| Stock `main.py`                                                                                                   | reopens the last app (`state["running"]`) unless it is gone or the wake reason is `WAKE_RESET`                    | always opens the menu; eats the waking press first with `badge.poll()`                                                                                                                                   | `vendor/badger2350/firmware/main.py`, `vendor/tufty2350/firmware/main.py`                                                                        |
| Menu                                                                                                              | remembers the selected app                                                                                        | starts at the first app (`active = 0`), apps alphabetical, 6 per page                                                                                                                                    | `vendor/tufty2350/firmware/apps/menu/__init__.py`                                                                                                |
| HOME                                                                                                              | `do_exit()` (the app's `on_exit`), then `clear_running()`, which makes the menu the app to reopen, then `reset()` | `do_exit()`, then `reset()`; there is no `clear_running()`                                                                                                                                               | `vendor/badger2350/modules/common/badgeware/__init__.py`, `vendor/tufty2350/modules/common/badgeware/__init__.py` (`launch`, `quit_to_launcher`) |
| `reset()`                                                                                                         | HOME is also BOOT on both, so it waits for HOME to be released, then `machine.reset()` (a watchdog reboot)        | same                                                                                                                                                                                                     | same files (`reset`)                                                                                                                             |
| Any other `machine.reset()` (`mpremote ... reset`, the badge tools, probably the restart after a disk-mode eject) | reopens the last app, because nothing changed `state["running"]`                                                  | the stock `main.py` opens the menu                                                                                                                                                                       | `vendor/badger2350/firmware/main.py`, `vendor/tufty2350/firmware/main.py`                                                                        |
| Restart reason                                                                                                    | `powman.get_wake_reason()`                                                                                        | same codes: HOME and any `machine.reset()` give `WAKE_WATCHDOG` 0xf2 (242), RESET `WAKE_RESET` 0xf1 (241), double-tap `WAKE_DOUBLETAP` 5, a front button `WAKE_BUTTON_*`, USB plug-in `WAKE_VBUS_DETECT` | `vendor/tufty2350/modules/c/powman/bindings.c`, `vendor/badger2350/modules/c/powman/bindings.c`                                                  |
| Double-tap RESET                                                                                                  | disk mode                                                                                                         | disk mode, handled before `main.py` runs                                                                                                                                                                 | `vendor/tufty2350/modules/common/main.py`                                                                                                        |
| Hold RESET                                                                                                        | the same power-off code is in the source; not tried                                                               | case lights fade, then power off; a front button turns it on                                                                                                                                             | `vendor/badger2350/modules/c/powman/powman.c`, `vendor/tufty2350/modules/c/powman/powman.c` (`handle_long_press`)                                |
| Waking button press                                                                                               | reaches the first `badge.poll()`                                                                                  | same; `run()` polls before the first `update()`, so the app sees it as pressed                                                                                                                           | `vendor/tufty2350/modules/c/input/input.cpp`                                                                                                     |
| Disk-mode drive                                                                                                   | `BADGER`                                                                                                          | `TUFTY`                                                                                                                                                                                                  | `vendor/badger2350/board/mpconfigboard.cmake`, `vendor/tufty2350/board/mpconfigboard.cmake` (`PIMORONI_FATFS_LABEL`)                             |
| `State`, filesystem helpers                                                                                       | same                                                                                                              | same                                                                                                                                                                                                     | `vendor/tufty2350/modules/common/badgeware/state.py`, `vendor/tufty2350/modules/common/badgeware/filesystem.py`                                  |
| Fonts                                                                                                             | same set                                                                                                          | same                                                                                                                                                                                                     | `vendor/tufty2350/romfs/fonts`                                                                                                                   |
| Power source                                                                                                      | `badge.usb_connected()`                                                                                           | same                                                                                                                                                                                                     | `vendor/tufty2350/modules/common/badgeware/badge.py`                                                                                             |
| Scaled blit                                                                                                       | -                                                                                                                 | `screen.blit(img, rect(x, y, w, h))`, as `fatal_error` does                                                                                                                                              | `vendor/tufty2350/modules/common/badgeware/__init__.py`                                                                                          |

## Rules for app code

- **Never assume the screen keeps its image.** True on the e-ink only;
  on the Tufty the run loop clears the screen before every `update()`.
- **On the Tufty, draw everything every frame.** Anything not drawn in
  this `update()` is gone after the next `display.update()`.
- **On the Badger, refresh only on a change.** Each `badge.update()` is
  a full, blocking e-ink refresh of about a second.
- **Save before refreshing or sleeping.** A deep sleep or a pulled
  battery loses anything not saved.
- **Branch on `badge.model`** (`"badger"`, `"tufty"`), never on drive
  names or screen size guesses.
- **Guard Badger-only names** (`NON_BLOCKING`, `wait_for_button_or_alarm`,
  `badge.first_update`): only use them on the Badger code path.
- **HIRES on the Tufty** for anything taller than 120 px.
- **Don't use `color.white`/`color.black` for true black and white on
  the Tufty.** They are tinted there; use `color.rgb()`.

## How the Dice Roller handles them

Everything badge-specific lives in `apps/dice_roller/devices/`; the game
(`game/`) and the saved record's rules (`saving/record.py`) use no
Badgeware names, so they test on a desktop. `saving/store.py` is the
only file that touches `State`.

- **One display module per badge.** `display_for(badge.model)` in
  `devices/__init__.py` imports only that badge's module
  (`devices/tufty.py`, `devices/badger.py`), so the other costs no
  memory. Any other model gets `devices/unsupported.py`, a short
  message pushed once with `display.update()`.
- **The display contract.** `__init__.py` calls `view.begin_frame()`
  before reading the buttons and `view.end_frame(app, now)` after the
  actions are applied and any save. Between them the display owns every
  per-frame step that differs: polling, clearing, drawing, pushing the
  frame and waiting. `devices/buttons.py` maps `BUTTON_*` to the game's
  names, the same on both badges.
- **Tufty (`devices/tufty.py`).** `badge.mode(HIRES)` for 320x240, then
  `end_frame()` only draws: `run()` polls, clears and pushes every
  frame. Rolls animate for `ROLL_ANIM_MS` using `app.rolled` and
  `app.rolled_at`. Colours come from `color.rgb()`.
- **Badger (`devices/badger.py`).** No `badge.mode()` call (the Badger
  has one resolution, and `mode()` would reset its refresh flags).
  `end_frame()` redraws and calls `badge.update()` (push, clear, poll)
  only when `app.changes` has moved since the last refresh; there is no
  roll animation. It then keeps polling with `badge.poll()` while a
  button is held, so a long press is measured, and otherwise waits in
  `wait_for_button_or_alarm(timeout=SLEEP_AFTER_MS)`, which on battery
  puts the badge to sleep after 30 s
  (`vendor/badger2350/modules/common/badgeware/__init__.py`). A press
  wakes it by restarting the app, which shows the saved roll again.
- **The Badger's four greys.** The panel keeps four levels, and only
  equal-channel greys survive: a colour washes out (`color.light_grey`,
  0xC0, lands on white). `devices/badger.py` uses black, dark (96),
  light (160) and white; the simulator reduces frames to 0, 85, 170 and
  255, which `tests/test_sim_badger.py` reads as bands.
- **Saving.** `DiceApp.take_save_point()` is true after every roll,
  lock, unlock and accept; `__init__.py` saves then, before
  `end_frame()` can refresh or sleep.
- **The waking press.** A press that launches the app (the menu's B) or
  wakes the Badger only does that: `game/controls.py` ignores buttons
  for `STARTUP_IGNORE_MS` after start-up.
- **Presses during a refresh are dropped** on the Badger, as in
  Pimoroni's own Badger apps. Holds only count while watched
  (`MAX_FRAME_GAP_MS`), so a hold across a refresh restarts.

To add a badge, follow the README's "Adding a badge" section.

## What only hardware shows

The table comes from the firmware source, and the simulator doesn't
model sleep, battery power, the e-ink refresh time or the real screen's
colours. The README's "Badger notes" record what the app does on a real
Badger; when a badge shows something that contradicts a row here,
update the row and say it was seen on hardware.
