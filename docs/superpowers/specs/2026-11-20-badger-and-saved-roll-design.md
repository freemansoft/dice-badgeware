# Badger 2350 support and a saved last roll: design

Builds on `2026-11-19-dice-roller-design.md`. Where the two disagree,
this document wins.

## Intent

Run the dice roller on the Badger 2350 as well as the Tufty 2350. The
user has a Badger to test on. The Badger's e-ink screen and its
power-off sleep change two things:

- **No animation.** The roll flicker and the flickering total are
  dropped. Rolled dice and the total go straight to their new values.
- **Resume after sleep.** On battery, the Badger switches itself off
  after a pause and restarts the app from scratch on the next press.
  Today that would bring back freshly rolled dice with every lock gone,
  while the screen still shows the old numbers. The app must instead
  come back exactly as it was. Every badge therefore saves the last roll
  (each die's value and lock) alongside the setup, and restores it at
  launch.

## Goals

- A Badger display that shows the same two screens, the same buttons
  and the same button labels as the Tufty, in the Badger's four greys.
- Locked dice look the way the user asked: **a white die with black
  numbers, inside a grey box** (the user's design).
- Saving and loading behave the same on every badge (the user's
  decision).
  - The saved file holds the setup plus the last roll: each die's value
    and whether it is locked.
  - It is saved after every roll, lock, unlock and Setup → Done (the
    user's decision; locks were added after testing, see "Revisions").
  - At launch the app shows the saved dice instead of rolling fresh.
- The Badger version can be tested here in the local simulator, like
  the Tufty.

## Non-goals

- Blinky 2350.
- Saving the highlight position, or un-accepted edits on the Setup
  screen.
- Any change to the Tufty's look or its roll animation.
- Faster or partial e-ink refresh. The v3.1.1 firmware has none: every
  refresh is a full one of about a second.

## Anti-goals

- **Changing numbers on wake.** The badge must never wake showing
  different dice from the ones on screen before it slept.
- **Losing the saved file.** An old file, which has no saved roll, must
  load cleanly: setup kept, fresh roll. A damaged file falls back as it
  does today.
- **Battery drain.** The app must not drain the Badger's battery by
  keeping it awake.

## Approaches (when to save the roll)

The user first picked A, then narrowed it: save after each roll, not
on lock or unlock. After testing on the Badger they went back to A (see
"Revisions"). The table shows A as first offered.

| | Approach | Trade-off |
|---|---|---|
| **A (picked)** | Save whenever the dice change: roll, lock, unlock all, Setup accepted. | One rule on every badge, and nothing is lost to a sudden power-off. Costs one small flash write per roll or lock, which is fine for hand presses. |
| B | Save only just before the Badger sleeps. | Fewer writes. But the Badger display would need its own sleep timer and would trigger saving, so the badges would behave differently, and a power cut would lose the roll. |
| C | Save on every press, including moving the highlight. | The highlight would also survive sleep. But A/C presses on the Tufty would mean a write each, for a small gain. |

The user picked A and asked for the same behaviour on every platform.

## Saved file

The file is still `/state/dice_roller.json`, written by Badgeware's
`State`. It gains two six-entry lists, one per dice slot, kept in step
with `faces`:

```json
{"count": 4, "faces": [6, 6, 6, 6, 6, 6],
 "values": [3, 5, 1, 6, 1, 1], "locked": [false, true, false, false, false, false]}
```

- `values`: what each die shows, 1 up to that slot's faces.
- `locked`: whether each die is locked.
- **Repair rules.** The file is repaired on load, never trusted, as
  today:
  - A missing, malformed or wrong-length `values` means there is no
    saved roll, so the app rolls fresh as today. In that case `locked`
    is ignored.
  - With `values` present:
    - each entry is clamped to 1..faces of its slot, and a non-number
      becomes 1;
    - each `locked` entry is true only if it is the boolean `true`;
    - a missing `locked` means nothing is locked.
- **When it is saved (the user's decision, revised after testing):**
  - After every roll that rolled at least one die.
  - After a lock toggle, and after unlock all when something was locked
    (unlock all with nothing locked changes nothing and doesn't save).
  - After Setup → Done, which always re-rolls, so it always saves.
  - Not on a highlight move or a Setup edit before Done.
- **At launch:** if a saved roll survives repair, the dice show those
  values and locks, on the roll screen, with the highlight on the first
  die and no animation. Otherwise the app rolls fresh.
- **Hidden dice.** Dice hidden by a lower count keep their saved value
  and lock in the file. Done re-rolls every die anyway, so a hidden
  die's old value is never shown.

### What is not saved (documented for users)

The dice and their locks are kept. These are not saved (the user's
decision) and are lost on a restart, on HOME, or when the Badger sleeps:

- **On the Setup screen:** any change made before Done. The badge comes
  back with the setup as it was at the last Done.
- **The highlight** always comes back on the first die.

The README's "Saved setup" section says this in these terms, next to
the new file format.

## Badger screen

264 × 176 pixels. The driver keeps four shades, chosen by OR-ing the
red, green and blue values, so only equal-channel greys are used:

| Shade | RGB |
|---|---|
| black | (0, 0, 0) |
| dark grey | (96, 96, 96) |
| light grey | (160, 160, 160) |
| white | (255, 255, 255) |

`color.light_grey` (0xC0) lands in white's band, so it is not used.

### Layout

The Tufty's layout, scaled to the smaller screen:

- a title bar across the top;
- a bar along the bottom for the A, B and C labels;
- a column down the right edge for the UP and DOWN labels;
- the dice spread evenly in the remaining area by `dice_layout.grid_slots`.

```
+------------------------------------------+--------+
| Roll Baby Roll                 Total 14  |        |   title bar (black, white text)
+------------------------------------------+        |
|   +----+     +----+     +----+           |  Lock  |   UP
|   | 3  |     | 5  |     | 1  |           | hold:  |
|   +----+     +----+     +----+           |  all   |
|      +----+     +----+                   |        |
|      | 6  |     | 2  |                   |  Roll  |   DOWN
|      +----+     +----+                   |        |
+------------------------------------------+--------+
|    Left          Setup          Right             |   A  B  C
+---------------------------------------------------+
```

### Look

**Dice**

| State | How it's drawn |
|---|---|
| Unlocked | White die, black outline, black number, small "d6" label. |
| Locked | The same white die with black numbers, inside a light-grey box (the user's design). |
| Highlighted | A thick black frame around the die. On a locked die it goes outside the grey box. |

**Title bars**

| Screen | Title bar |
|---|---|
| Roll | Black bar, white text: "Roll Baby Roll" on the left, "Total N" on the right. |
| Setup | Dark-grey bar with white text: "Setup", and "Dice N" on the right. Shown as a white pill when the count is highlighted, as on the Tufty. |

The two bar shades tell the screens apart without colour.

**Labels** come from the same `LABELS` and `HOLD_LABELS` as the Tufty,
in black on white. Their positions follow the Badger's buttons: A, B
and C evenly along the bottom, UP about a third of the way down the
right edge, DOWN about three-quarters of the way.

**Text** uses MonaSans with 4× anti-aliasing, like the Tufty. Edges
snap to the four shades, which Pimoroni's own vector-text demo shows is
fine. If the font fails to load, the ROM pixel font is used instead.

*Claude's calls:* every colour, the shades, the bar heights and the
label positions above. Label positions are estimated from Pimoroni's
render and need checking on the user's badge.

### How the Badger runs

The Badger's `run()` loop only calls `update()`: it doesn't poll, clear
or refresh. Badger's display file owns all of that through the existing
contract:

- **`begin_frame()`** polls the buttons.
- **`end_frame(app, now)`** checks whether to refresh.
  - It refreshes only when `app.changes` has moved, or on the first
    frame after launch.
  - To refresh, it draws the whole screen, then calls `badge.update()`.
    That pushes the frame, clears the buffer and polls. The frame is
    always redrawn first, because the buffer is cleared after each
    refresh.
  - It then waits for the next press with the firmware's
    `wait_for_button_or_alarm(timeout=…)`. On battery, that powers the
    badge off once the timeout passes. On USB it never sleeps.
- **Presses during a refresh are dropped (the user's decision).**
  - Refreshes block, using the firmware's default mode, so a press made
    and released while the screen refreshes is not seen. This matches
    Pimoroni's own Badger apps.
  - Quick repeated presses therefore move the highlight less than the
    number of presses. Press, wait for the screen, then press again.
  - Holding UP shows the single lock first, then a second refresh once
    the hold counts as "unlock all".
  - The README's Badger notes say this.
- **The long press must still work.** Holding UP for about a second
  unlocks all dice. While any button is held, the display keeps polling
  instead of waiting for a new press, so the 800 ms hold is measured.
  A gap of more than 250 ms between frames (a refresh) restarts the
  hold, so a second tap during a refresh can't unlock every die.
- **The waking press only wakes** (the user's decision, revised after
  testing). After a wake, the firmware hands the button that woke the
  badge to the first poll. The app ignores buttons for 400 ms after
  every launch, from the menu or from a wake, so that press is not
  taken as an action: the menu's B press can't open Setup, and pressing
  DOWN to wake doesn't roll.
- **Sleep timeout:** 30 seconds without a press, the firmware's default.
  *Claude's call.*
- **No `HIRES` on the Badger.** `badge.mode(HIRES)` is not called there.

## Simulator

The same set-up as the Tufty, with a second model:

- **Firmware:** add the `pimoroni/badger2350` firmware at v3.1.1 as a
  submodule at `vendor/badger2350`.
- **Wasm build:** fetch `badgeware-badger2350-asyncify` with
  `tools/update_sim.py --models tufty,badger`. It is already published
  in the pinned run, but GitHub deletes it about 22 December 2026, so
  fetch it soon.
- **Wiring:** add `badger` to:
  - `MODELS` in `sim/stage.py` and `sim/run_headless.mjs`;
  - the landing page;
  - `sim/wasm/VERSION.json`.
- **Headless runs** return 264 × 176 frames for the Badger.
- **Tests:**
  - **Badger simulator tests** mirror the Tufty ones:
    - both screens draw;
    - the labels appear;
    - a locked die shows its grey box;
    - a roll's first frame already shows the final values (no flicker);
    - a relaunch after a roll shows the same dice and locks.
  - **Host tests** cover:
    - repair of the new fields;
    - which actions queue a save;
    - restoring a saved roll at launch.

## Left to the builder

- Exact sizes, line weights and font sizes on the Badger.
- How the Badger display measures the long press while polling.
- Whether the e-ink simulator needs anything the Tufty's didn't, such
  as when it calls `blitrgba` or what it does on sleep.
- How `DiceApp` takes a saved roll (for example an optional argument),
  as long as the core stays free of Badgeware names.

## Revisions after testing on the Badger (2026-11-20)

The sections above have been updated to match; this records what
changed and why.

The final review found that two decisions above combined badly: locks
were not saved, and the press that woke the badge also acted. Lock some
dice, let the Badger sleep, press DOWN, and the dice the screen showed as
locked were rolled; a press that woke a badge asleep on Setup acted on the
roll screen. The user reversed both, for every badge:

- **Locks are saved.** Lock, unlock and unlock all are save points, as
  well as every roll and Done. Unlock all with nothing locked changes
  nothing (no save, no refresh). This supersedes "Locking and unlocking
  don't save" and the "Between rolls" line under "What is not saved".
- **The waking press only wakes.** The 400 ms ignore window at launch now
  applies after a wake too, so the waking press is not taken as an
  action. This supersedes "The waking press counts" and the
  `woken_by_button()` exception.

Also from testing: the Badger's button labels are larger (size 19, the
hold hint 11) and a locked die's grey box fills its slot (an 8 px band),
with the highlight ring just outside. A long UP press only counts while
the app watches it: a gap of more than 250 ms between frames (the
Badger's blocking refresh) restarts it, so a second tap during a refresh
can't unlock every die.

After a second look on the Badger: the line above the bottom labels moved up 3 px (BAR_TOP 151, labels unchanged), and Roll moved up 6 px (DOWN label y 132) to line up with the DOWN button.
