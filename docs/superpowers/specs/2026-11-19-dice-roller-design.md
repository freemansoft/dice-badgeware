# Dice Roller for Badgeware: design

Date: 2026-11-19. Status: draft for approval.

## Intent

A dice app for Pimoroni's Badgeware badges, launched from the badge's
home menu. It suits games where you roll a handful of dice, keep some,
and reroll the rest (Yahtzee-style), and works for plain "roll N dice"
too. Up to six dice, each with 4 to 20 faces, laid out like the home
menu's 3×2 grid of app icons.

The first target is the **Tufty 2350**. The app is structured so the
**Badger 2350** and **Blinky 2350** can be added later by writing one
new display file each, without touching the dice, the screens' logic
or the buttons.

## Goals

- Start straight on the roll screen with the saved configuration, or
  4 six-sided dice the first time.
- Roll all unlocked dice, lock and unlock individual dice, unlock all.
- A configure screen to set the number of dice (1–6) and each die's
  faces (4–20).
- Save the configuration as JSON so it survives leaving the app,
  sleep and reset.
- Everything driven by the five user buttons (A, B, C, UP, DOWN).
- Readable at arm's length: big numbers on the Tufty's 320×240 screen.
- Well structured: the dice in their own file, the display in its own
  file, and nothing outside the display files knowing which badge it
  runs on.

## Non-goals

- Badger and Blinky displays in this round (the structure supports
  them; the files aren't written).
- Saving rolled values or locks between launches.
- Dice notation, modifiers, roll history, scoring for any game.

## Anti-goals

- A press that does something you didn't see coming: every button has
  one job per screen, apart from the documented short/long UP.
- Laggy input: no double-press detection, which would delay single
  presses.
- Badge-specific `if model == ...` checks scattered through the code.

## Constraints

- Badgeware MicroPython app: `apps/dice_roller/__init__.py` with
  `update()` passed to `run()`, plus a 24×24 `icon.png`. The folder
  name gives the menu label **Dice Roller**.
- HOME is reserved by the firmware (exits to the menu); the other five
  buttons are the app's, and are the same on all three badges.
- The menu launches an app on a **B** press, and B opens configure in
  this app, so buttons are ignored for about 400 ms after launch (as
  claude-buddy-badgeware does) so the launch press can't open
  configure.
- Badge API used: `badge.pressed/held`, `badge.ticks`, `badge.model`,
  `badge.mode(HIRES)`, `screen` drawing, `shape`, `color`, `font`,
  `State.load/save`.
- Lint: Pimoroni's ruff rules (as in claude-buddy-badgeware's
  `ruff.toml`).

## Approaches

One sensible way, so no real alternatives were weighed:

- **Chosen:** a core of pure-Python files that know nothing about the
  badge (dice, app state and screens, button handling, layout maths,
  saved configuration), plus one display file per badge that only
  draws. The entry file picks the display from `badge.model`. The core
  runs under CPython for host unit tests. This is the same split as
  claude-buddy-badgeware's model/view/profile.
- Rejected: one monolithic `__init__.py` (can't test the logic off
  the badge, and every badge would need its own copy of it); the
  Tufty's 160×120 low-res mode (numbers would be small and blocky).

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

## Saved configuration

Saved with Badgeware's built-in `State` helper under the name
`dice_roller`, which writes `/state/dice_roller.json`:

```json
{"count": 4, "faces": [6, 6, 6, 6, 6, 6]}
```

- `count`: number of dice in use, 1–6.
- `faces`: faces for all six dice slots, 4–20 each, including slots
  beyond `count`, so lowering and raising the count brings dice back
  as they were.
- Loaded once at startup with `State.load`; defaults are 4 dice, all
  d6. A missing or unreadable file falls back to the defaults (`State`
  handles that).
- *Claude's call:* values read from the file are repaired, not
  trusted: `count` clamped to 1–6, `faces` padded or trimmed to six
  entries, each clamped to 4–20, anything non-numeric replaced by 6.
- *Claude's call:* saved only when B accepts on the configure screen,
  and only if something changed.
- The file is the same on every badge.

## Structure

### Files

```
apps/dice_roller/
  __init__.py       entry: picks the display from badge.model, loads the
                    config, runs the update() loop. The only file that
                    touches badge input and State.
  dice.py           Die and DiceSet: faces, value, locked, roll, lock
                    toggle, unlock all, total. Pure Python.
  dice_config.py    defaults, repair, to/from the JSON dict. Pure Python.
  dice_app.py       the two screens: which is showing, highlight
                    position, config editing, and what each action
                    does. Owns a DiceSet. Pure Python.
  dice_input.py     turns pressed/held buttons and ticks into actions,
                    including the UP long press. Pure Python.
  dice_layout.py    slot positions for any screen size: the menu's 3×2
                    grid scaled to fit, plus a header strip. Pure Python.
  display_tufty.py  draws both screens on the Tufty (HIRES, colour,
                    roll animation). The only Tufty-specific file.
  icon.png          24×24, generated by tools/make_icon.py
tests/              CPython unittest for every pure-Python file
tools/install.py    copy the app to the badge's USB drive
tools/make_icon.py  regenerate icon.png (no dependencies)
ruff.toml           Pimoroni lint rules
README.md           what it is, buttons, install, development
```

### How the pieces talk

```
buttons + ticks ──► dice_input ──► action (LEFT, RIGHT, LOCK, UNLOCK_ALL,
                                           ROLL, CONFIGURE, INC, DEC, ACCEPT)
                                      │
                                      ▼
                         dice_app (uses dice.py, dice_config.py)
                                      │  state + change counter
                                      ▼
                         display_<badge>.draw(app, now)
```

- Actions are plain names, not buttons. The button → action mapping is
  in `dice_input`, the same for every badge.
- `dice_app` keeps a **change counter** that goes up whenever anything
  visible changes. The Tufty display ignores it and redraws every
  frame; a Badger display would redraw only when it changes, because
  every e-ink refresh is a 1–2 s flash.
- A roll changes the dice values **at once** in `dice_app`, and
  records which dice rolled and when. The flicker is drawn by the
  display from that, so animation is a display choice: the Tufty
  animates, a Badger display wouldn't.

### The display contract

Each `display_<badge>.py` provides one class with:

- `__init__(screen size)`: set the display mode, fonts and colours,
  build the layout with `dice_layout`.
- `draw(app, now)`: draw whichever screen `app` says is showing.
- `needs_redraw(app, now)`: True every frame on Tufty and Blinky;
  only on a change-counter change on Badger.

`__init__.py` holds a table from `badge.model` to display class. A
badge with no display file yet shows a one-line "not supported yet"
message.

### What later badges would need

| | Tufty 2350 (now) | Badger 2350 (later) | Blinky 2350 (later) |
|---|---|---|---|
| Screen | 320×240 colour (HIRES) | 264×176, black, white, 2 greys | 39×26 white LEDs |
| Layout | 3×2 grid, menu scaled 2× | Same 3×2 grid scaled to fit | 3×2 grid of 13×13 cells, tiny pixel font, header dropped |
| Redraw | Every frame | Only on a change | Every frame |
| Roll animation | Flicker ~500 ms | None | Short flicker |
| Locked look | Muted colour + lock tag | Grey fill | Dim cell |

None of this needs changes outside a new `display_<badge>.py` and one
line in `__init__.py`'s table. Badger's usual "sleep between updates"
is out of scope; the app stays awake while open.

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
  keep their faces (they stay in the saved `faces` array), so raising
  the count again brings them back as they were.
- **Leaving configure (B)** saves the configuration if it changed,
  then returns to the roll screen with a fresh roll and all dice
  unlocked; the highlight goes to die 1.
- **Roll animation (Tufty):** each rolling die flickers through random
  values for about 500 ms, then shows its result. Locked dice don't
  move. Buttons still work during it; DOWN during it starts a new
  roll.
- **Total** of all dice shown in the roll screen's header.
- **Locked look (Tufty):** a locked die is drawn in a muted colour
  with a small padlock/"LOCK" tag; the highlighted die gets a bright
  outline. Dice colours reuse the menu's icon palette (orange, blue,
  red, green, yellow, grape) by slot.
- **Layout (Tufty, 320×240):** the menu's grid scaled 2×: slot centres
  at x = 64, 160, 256 and y = 84, 180, squircle half-size about 40 px.
  Header strip across the top for the total (roll screen) or the dice
  count field (configure screen), with short button hints.
- **Randomness:** MicroPython `random`, seeded once at start from
  `os.urandom` when available. `dice.py` takes the random function as
  a parameter so tests can make rolls predictable.

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
