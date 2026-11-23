# Dice Roller for Badgeware

A dice app for Pimoroni's [Tufty 2350](https://shop.pimoroni.com/products/tufty-2350)
and Badger 2350 badges (Badgeware firmware). Roll two to six dice, each
with 4 to 20 faces, lock the ones you want to keep, and reroll the rest,
Yahtzee-style.

The game is the same on every badge; only the drawing differs, one file
per badge, so the Blinky 2350 can be added later (see
[Adding a badge](#adding-a-badge)).

## Buttons

### Roll screen (where the app starts)

| Button                  | Action                                                  |
| ----------------------- | ------------------------------------------------------- |
| A / C                   | Move the highlight left / right; wraps across both rows |
| UP                      | Lock the highlighted die (press again to unlock it)     |
| UP, held about a second | Unlock all dice                                         |
| DOWN                    | Roll every unlocked die                                 |
| B                       | Open the configure screen                               |

The title bar reads **Roll Baby Roll**, with the total on the right; while
the dice flicker after a roll, the total flickers with them. Every
die is dark red; locked dice turn grey and are labelled `LOCK`. On the
Badger's black-and-white screen dice are white, and a locked die turns
grey.

### Configure screen

The title bar reads **Setup**, with the dice count on the right.

| Button    | Action                                                          |
| --------- | --------------------------------------------------------------- |
| A / C     | Move between the dice count and each die                        |
| UP / DOWN | Increase / decrease what is highlighted                         |
| B         | Accept and go back to rolling (a fresh roll, all dice unlocked) |

A label next to each button always shows what it does: A, B and C are
labelled along the bottom of the screen, UP and DOWN down its right edge.

Dice count: 2–6. Faces per die: 4–20. Values stop at the ends rather than
wrapping. The dice are spread evenly in rows spaced like the home menu's
icons: 2 or 3 in one row, 4 as 2+2, 5 as 3+2, 6 as 3+3.

HOME always returns to the Badgeware menu.

## Saved setup

The setup and the last roll are saved in `/state/dice_roller.json` on the
badge, on every badge, after every roll, every lock or unlock, and every
time you press Done on the Setup screen:

```json
{
  "count": 4,
  "faces": [6, 6, 6, 6, 6, 6],
  "values": [3, 5, 1, 6, 1, 1],
  "locked": [false, true, false, false, false, false]
}
```

When the app starts (or the Badger wakes from sleep) it shows those dice
again, locks included, exactly as they were on screen, instead of rolling
fresh. The first launch uses 4
six-sided dice. Each list covers all six dice, so lowering the count and
raising it again brings dice back as they were. A hand-edited or damaged
file is repaired on load (values pulled into range, anything unreadable
replaced by the defaults); an older file without `values` keeps its setup
and starts with a fresh roll.

On a restart, HOME or sleep these are not kept:

- changes on the Setup screen before you press Done (the app comes back
  on the roll screen with the setup as it was at the last Done);
- where the highlight was (it starts on the first die).

The press that starts the app or wakes the badge only does that: it
isn't also taken as Roll, Lock or anything else, since it was meant for
whatever screen you were looking at before.

## Install

1. Connect the badge with a USB-C data cable and **double-tap RESET** on
   the back. It mounts as a drive named `TUFTY` or `BADGER`.
2. Run `python3 tools/install.py`. It finds the drive, copies
   `apps/dice_roller/` into its `apps/` folder, and on macOS and Linux
   ejects it. (Or copy the folder by hand, then eject.)
3. The badge restarts into the menu. Choose **Dice Roller**.

The installer is hardened. It builds the new copy in a hidden folder on
the drive, checks every file byte for byte, and only then swaps it in, so
an interrupted or bad copy (a RESET, a pulled cable, a full drive) leaves
the old app in place and working: just run it again. It also removes the
`._` files macOS writes beside every file on the badge. Only
`apps/dice_roller` is replaced; other apps and your saved dice stay.

Always eject before pressing RESET or unplugging: the check can't tell
whether the computer has finished writing to the badge, and files cut
short show up as a SyntaxError when the app starts.

### Badger notes

- There is no roll animation: each change is one full e-ink refresh of
  about a second, straight to the final dice and total.
- Presses made while the screen refreshes are dropped (as in Pimoroni's
  own Badger apps): press, wait for the screen, press again.
- To unlock all dice, hold UP until the screen has changed twice (the
  first refresh shows the single lock).
- On battery the badge sleeps after 30 seconds without a press. Any
  button wakes it where you left off, locks included (see
  [Saved setup](#saved-setup)); that press only wakes it, so press again
  to roll.

## Development

```sh
git submodule update --init          # vendor/: Pimoroni's Tufty and Badger firmware, pinned to a release
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
git config core.hooksPath .githooks  # pre-commit: block unformatted Markdown
```

Using Claude Code? Also install the project's plugins: see
[Claude Code](#claude-code).

| Task                                  | Command                                                                                                 |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| All tests (unit + simulator)          | `.venv/bin/pytest`                                                                                      |
| Lint everything with Pimoroni's rules | `.venv/bin/ruff check .`                                                                                |
| Check MicroPython syntax              | `find apps/dice_roller -name '*.py' -print0 \| xargs -0 -n1 .venv/bin/python -m mpy_cross -o /dev/null` |
| Format Markdown                       | `git ls-files -z '*.md' \| xargs -0 npx --yes prettier@3.9.10 --write`                                  |
| Regenerate the icon                   | `python3 tools/make_icon.py`                                                                            |

The simulator tests need Node (18 or later) and are skipped without it.

`ruff.toml` extends the rules Pimoroni lint their own badge firmware with
(`vendor/tufty2350/ci/ruff.toml`), so it needs the submodules. Unused
arguments that a fake must keep, to match the real signature, start with
`_`. Python has no formatter: Pimoroni don't use one either.

Markdown is formatted with prettier (pinned version, settings in
`.prettierrc.json`, as in claude-buddy-badgeware). The pre-commit hook in
`.githooks/` blocks commits whose staged `.md` files aren't formatted and
prints the command to fix them. It needs Node; turn it on once per clone
with the `git config` line above.

GitHub Actions (`.github/workflows/ci.yml`) runs the lint, the syntax
check, every test (simulator included) and the Markdown check on each
pull request and each push to `main`. `requirements-dev.txt` pins the tool versions so a new
ruff release can't fail a build on its own.

### Project layout

The app is split by concern: the game (the same everywhere), saving, and
the badge-specific code, each in its own folder. `__init__.py` only
connects them.

```
apps/dice_roller/        the app (copied to the badge)
  __init__.py            entry: loads the saved record, picks the display, runs the loop
  game/                  the rules and screens (plain Python, every badge)
    dice.py              Die and DiceSet, faces and dice-count limits
    app.py               the two screens, the highlight and the dice; says when to save
    controls.py          buttons -> actions, long press, button labels
    layout.py            where dice go on any screen size
  saving/                the saved record
    record.py            what is saved: defaults, repair, snapshot (plain Python)
    store.py             reading and writing it with Badgeware's State
  devices/               everything badge-specific
    __init__.py          display_for(badge.model)
    buttons.py           badge buttons -> game names
    tufty.py             Tufty 2350 display (colour, roll animation)
    badger.py            Badger 2350 display (e-ink, four greys, sleep)
    unsupported.py       message for a badge with no display yet
  icon.png               24x24 menu icon (tools/make_icon.py)
sim/                     local simulator (below)
tests/                   pytest: one file per module, plus the simulator
tools/install.py         copy the app to the badge's USB drive
tools/make_icon.py       regenerate icon.png
tools/update_sim.py      check for and pull newer simulator builds and firmware
vendor/                  Pimoroni's Tufty and Badger firmware (git submodules)
docs/superpowers/        designs and implementation plans
ruff.toml                lint rules (extends Pimoroni's)
.githooks/pre-commit     block commits of unformatted Markdown (prettier)
.github/workflows/ci.yml lint, syntax check and tests on every PR
.claude/skills/          the project's own Claude Code skill (badge-deploy)
```

### Simulator

`sim/` runs the real Tufty and Badger firmware Python and the unmodified
app inside Pimoroni's WebAssembly MicroPython builds from
[pimoroni/badgeware-wasm](https://github.com/pimoroni/badgeware-wasm).

```sh
python3 sim/stage.py                       # builds sim/dist/ (not committed)
python3 -m http.server -d sim/dist 8000    # then open http://localhost:8000/tufty/ or /badger/
```

Click the page, then use `a`, `b`, `c` for A, B, C, the arrow keys for
UP and DOWN, and `h` for HOME.

Headless, for tests and quick checks:

```sh
node sim/run_headless.mjs --model tufty --steps "B,UP,B,DOWN,UP:1200" --frames out.json
node sim/run_headless.mjs --model badger --steps "UP,DOWN" --frames out.json --state saved.json
```

`--steps` is a comma-separated list of buttons, each optionally with a
hold time in milliseconds. `out.json` holds an RGB frame after each step
(320×240 Tufty, 264×176 Badger), the number of screen refreshes per
step, the saved record at the end, and the app's console output.
`--state` starts the app from a saved record, as after a restart.
`tests/test_sim.py` and `tests/test_sim_badger.py` check pixels in these
frames.

The Badger build runs deep on the JavaScript stack, so the headless
runner restarts Node with a 4 MB stack (Node 18's default overflows).
Browsers need nothing extra: the Badger page has been checked in Chrome
(it loads, draws and answers every button with no errors).

The simulator doesn't model sleep, battery power, the e-ink refresh time
or the real screen's colours, so check those on a badge.

### Updating the simulator

`sim/wasm/VERSION.json` records which badgeware-wasm build and which
firmware release are in use. badgeware-wasm publishes the build the
simulator needs only as a CI artifact, which GitHub deletes after 90
days, so the downloaded build is committed here.

```sh
python3 tools/update_sim.py --check   # pinned vs latest; exits 1 if newer
python3 tools/update_sim.py           # download the newest build, move the firmware submodule, re-stage
.venv/bin/pytest                      # does the app still work on the new versions?
git add sim/wasm vendor && git commit -m "Update simulator to ..."
```

Name every model when updating (`--models tufty,badger`); a model left out
is dropped from `VERSION.json`.

It needs the [GitHub CLI](https://cli.github.com), logged in (`gh auth
login`). `--run <id>` and `--firmware-tag <tag>` pick specific versions.

### Adding a badge

The Tufty and Badger are done; the Blinky 2350 is next.

1. Write `apps/dice_roller/devices/<model>.py` with a class that has
   `begin_frame()` (called before the buttons are read) and
   `end_frame(app, now)` (called after the actions are applied). These
   own everything about a frame that differs between badges:
   - The Tufty's `run()` loop polls the buttons, clears the screen and
     pushes each frame itself, so `tufty.py` only draws (and animates
     rolls with `app.rolled` and `app.rolled_at`).
   - The Badger's `run()` does none of that, so `badger.py` refreshes
     only when `app.changes` has moved, then waits for the next press.

   Read `tufty.py` for what `app` provides.

2. Add it to `display_for()` in `apps/dice_roller/devices/__init__.py`.
3. For the simulator: `git submodule add https://github.com/pimoroni/<model>2350 vendor/<model>2350`,
   run `python3 tools/update_sim.py --models tufty,badger,<model>`, and add
   the model to `MODELS` in `sim/stage.py` and to `MODELS` and `SETTLE` in
   `sim/run_headless.mjs`.

### Claude Code

The project uses two Claude Code plugins. They are not stored in this
repository; `.claude/settings.json` names them, and Claude Code fetches
them from GitHub:

| Plugin                                                             | From                                                                            |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `superpowers` (brainstorming, planning, TDD, code review and more) | [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace) |
| `skill-creator`                                                    | Anthropic's official marketplace, `claude-plugins-official`                     |

Set them up once per clone, from the repository folder:

```bash
claude plugin marketplace add obra/superpowers-marketplace
claude plugin marketplace add anthropics/claude-plugins-official
claude plugin install superpowers@superpowers-marketplace --scope project
claude plugin install skill-creator@claude-plugins-official --scope project
```

The two `marketplace add` lines make the plugin sources known to your
Claude Code (a new install doesn't have either yet); they are harmless if
you already have them. Re-running everything is safe, and none of it
changes files in the repository. Then start Claude Code, or run
`/reload-plugins` in a running session, and trust the folder when asked.
Superpowers' own start-up hook loads its `using-superpowers` skill into
each session, and its skills are named `superpowers:<skill>`.

To check: `claude plugin list` shows both as enabled.

Both marketplaces update themselves: Anthropic's by default, and the
Superpowers one because `.claude/settings.json` sets `"autoUpdate": true`.
New Superpowers releases arrive without any change to this repository.

One skill is the project's own and is stored here, in
`.claude/skills/`: `badge-deploy`, how Claude puts a branch on a real
badge for testing (checks first, the committed code via
`tools/install.py`, then what to look at on the badge). Claude Code
picks it up with no setup.

## Licence and credits

- `sim/wasm/` is Pimoroni's MIT-licensed
  [badgeware-wasm](https://github.com/pimoroni/badgeware-wasm) build;
  `vendor/tufty2350` keeps its own licence.
- `tools/install.py` and `tools/make_icon.py` are adapted from
  claude-buddy-badgeware, and the installer's staged, checked copy from
  MoodBadger2350's; the simulator loader follows the approach of
  MoodBadger2350's `sim/`.
- Button layout and menu spacing follow Pimoroni's Badgeware launcher.
