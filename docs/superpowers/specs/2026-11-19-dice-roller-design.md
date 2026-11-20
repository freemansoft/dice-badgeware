# Dice Roller for the Tufty 2350: design

Date: 2026-11-19. Status: draft for approval.

## Intent

A dice app for the Pimoroni Tufty 2350 (Badgeware firmware), launched
from the badge's home menu. It suits games where you roll a handful of
dice, keep some, and reroll the rest (Yahtzee-style), and works for
plain "roll N dice" too. Up to six dice, each with 4 to 20 faces,
laid out like the home menu's 3×2 grid of app icons.

## Goals

- Start straight on the roll screen with 4 six-sided dice.
- Roll all unlocked dice, lock and unlock individual dice, unlock all.
- A configure screen to set the number of dice (1–6) and each die's
  faces (4–20).
- Everything driven by the five user buttons (A, B, C, UP, DOWN).
- Readable at arm's length: big numbers on the 320×240 screen.

## Non-goals

- Saving the configuration between launches: every launch starts at
  4×d6, as asked.
- Dice notation, modifiers, roll history, scoring for any game.
- Badger or Blinky support (the code shouldn't make it hard later,
  but nothing is done for it now).

## Anti-goals

- A press that does something you didn't see coming: every button has
  one job per screen, apart from the documented short/long UP.
- Laggy input: no double-press detection, which would delay single
  presses.

## Constraints

- Badgeware MicroPython app: `apps/dice_roller/__init__.py` with
  `update()` passed to `run()`, plus a 24×24 `icon.png`. The folder
  name gives the menu label **Dice Roller**.
- HOME is reserved by the firmware (exits to the menu); the other five
  buttons are the app's.
- Badge API used: `badge.pressed/held`, `badge.ticks`,
  `badge.mode(HIRES)`, `screen` drawing, `shape`, `color`, `font`.
- Lint: Pimoroni's ruff rules (as in claude-buddy-badgeware's
  `ruff.toml`).

## Approaches

One sensible way, so no real alternatives were weighed:

- **Chosen:** a single Badgeware app split into a pure-Python model
  (dice state, cursor, locking, button → action logic including the
  long press) and a view (drawing only), the same split as
  claude-buddy-badgeware. The model runs under CPython for host unit
  tests.
- Rejected: one monolithic `__init__.py` (can't test the logic off
  the badge); the 160×120 low-res mode the menu uses (numbers would be
  small and blocky).

## Screens and buttons (as specified)

### Roll screen (start screen)

Shows the configured dice in the menu's 3×2 slot positions, row by
row: dice 1–3 on the top row, 4–6 on the bottom.

| Button | Action |
|---|---|
| A | Move highlight left; wraps from first die to last, and across rows |
| C | Move highlight right; wraps from last die to first, and across rows |
| UP (press) | Lock the highlighted die. *Claude's call:* if it is already locked, unlock it |
| UP (hold) | Unlock all dice |
| DOWN | Roll every unlocked die |
| B | Open the configure screen |

### Configure screen

A "number of dice" field, then one square per die showing its faces
(`d6`, `d20`, …).

| Button | Action |
|---|---|
| A | Move highlight left, wrapping across the count field and the die squares |
| C | Move highlight right, same wrapping |
| UP | Increase the highlighted value |
| DOWN | Decrease the highlighted value |
| B | Accept and return to the roll screen |

Ranges: count 1–6, faces 4–20, any whole number.

## Claude's calls (correct any of these)

- **Startup:** the dice show a fresh roll on launch, not blanks.
- **Long press:** UP held for 800 ms unlocks all. The short-press lock
  toggle happens on press, so a hold first toggles the highlighted die
  and then unlocks everything; the end state is "all unlocked" either
  way, and short presses have no delay.
- **Values clamp at the ends** (count stops at 1 and 6, faces at 4 and
  20) rather than wrapping, so you can't jump from d4 to d20 by
  accident.
- **New dice default to 6 faces.** Dice dropped by lowering the count
  keep their faces for the rest of the session, so raising the count
  again brings them back as they were.
- **Leaving configure (B)** returns to the roll screen with a fresh
  roll and all dice unlocked; the highlight goes to die 1.
- **Roll animation:** each rolling die flickers through random values
  for about 500 ms, then settles. Locked dice don't move. Buttons still
  work during the animation; DOWN during it restarts the roll.
- **Total** of all dice shown in the roll screen's header.
- **Locked look:** a locked die is drawn in a muted colour with a
  small padlock/"LOCK" tag; the highlighted die gets a bright outline.
  Dice colours reuse the menu's icon palette (orange, blue, red,
  green, yellow, grape) by slot.
- **Layout (320×240):** the menu's grid scaled 2×: slot centres at
  x = 64, 160, 256 and y = 84, 180, squircle half-size about 40 px.
  Header strip across the top for the total (roll screen) or the dice
  count field (configure screen), with short button hints.
- **Randomness:** MicroPython `random`, seeded once at start from
  `os.urandom` when available.

## Project layout

```
apps/dice_roller/
  __init__.py      entry: HIRES mode, update() loop, wires model + view
  dice_model.py    pure Python: dice, locks, cursor, config, actions
  dice_input.py    pure Python: button events + ticks -> actions (long press)
  dice_view.py     drawing only (Badgeware screen API)
  icon.png         24x24, generated by tools/make_icon.py
tests/             CPython unittest for model and input
tools/install.py   copy the app to the badge's USB drive
tools/make_icon.py regenerate icon.png (no dependencies)
ruff.toml          Pimoroni lint rules
README.md          what it is, buttons, install, development
```

## Verification

- Host: `python3 -m unittest discover -s tests`, `ruff check .`,
  `mpy-cross` on each app file.
- Optional: the `pimoroni-emulator` package on PyPI, if it runs this
  firmware's API, for a look at the screens before copying to the
  badge.
- On the badge: copy the app across and try both screens.

## Left to the builder

Exact fonts and sizes, colours beyond the palette above, the padlock
drawing, hint wording, and the icon artwork.
