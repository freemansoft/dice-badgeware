# dice-badgeware

Dice Roller: a MicroPython Badgeware app for the Pimoroni Tufty 2350 (colour LCD) and Badger 2350 (e-ink). One app folder, `apps/dice_roller/`, runs on both: the game in `game/` and `saving/` is plain Python, and everything badge-specific is in `devices/`, one display module per badge. See `README.md` for buttons, install, layout and the simulator.

## Development

- Set up: `git submodule update --init` (`vendor/`: Pimoroni's firmware, which ruff and the simulator need), then `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt` (pinned ruff, mpy-cross, mpremote, pytest), then `git config core.hooksPath .githooks`
- Test: `.venv/bin/pytest` (includes the headless simulator for both badges when `node` is installed)
- MicroPython syntax: `find apps/dice_roller -name '*.py' -print0 | xargs -0 -n1 .venv/bin/python -m mpy_cross -o /dev/null`
- Lint: `.venv/bin/ruff check .` (`ruff.toml` extends Pimoroni's `vendor/tufty2350/ci/ruff.toml`). `ruff format` is not used: Pimoroni's firmware CI only runs `ruff check`
- Markdown: `npx --yes prettier@$(cat .prettier-version) --config .prettierrc.json --write <files>`. The version lives only in `.prettier-version`; the hook and CI read it, and `tests/test_prettier_version.py` fails if it's written anywhere else
- Pre-commit hook (`.githooks/pre-commit`): on staged content, `ruff check` on `.py` files, mpy-cross on `apps/dice_roller` `.py` files, prettier on `.md` files
- CI (`.github/workflows/ci.yml`) runs the lint, MicroPython syntax, tests and Markdown checks on every PR and push to `main`
- Simulator: `python3 sim/stage.py && python3 -m http.server -d sim/dist 8000`, then `/tufty/` or `/badger/`. Headless: `node sim/run_headless.mjs --model badger --steps "UP,DOWN" --frames out.json`. `python3 tools/update_sim.py --check` compares the pinned build and firmware with the latest
- Project skills: `badgeware-platforms` (how the Badger and Tufty differ and the app's rules for both; read it before writing app code), `badge-verify` (which test layers a change needs, simulator and hardware checks, hand checklists), `badge-deploy` (firmware check, install the committed code, check the copy from the badge's side), `badge-firmware` (check or flash firmware) and `dice-docs` (Markdown standard, which doc owns what)
- Tools run as scripts from the repository root: `python3 tools/install.py`, and `.venv/bin/python tools/badge_info.py` (also `badge_check.py`, `flash_firmware.py`) for the ones that need `mpremote`
- Button presses on a real badge: end the turn with exactly what to press, and tell the user not to touch the badge until the tool says "Ejected" or "Flash complete". Never assume a press happened; read the result. Never run two installers against one drive
- Ad-hoc `mpremote`: take the port whose `mpremote devs` line names the badge you mean (`Tufty 2350` or `Badger 2350`; other boards are often plugged in too), and end with `reset` (`mpremote connect <port> exec "..." reset`), or the badge stays frozen on its last screen until RESET. After `reset`, a Badger reopens the app it was showing and a Tufty opens the menu. `/system` (the drive) is read-only from MicroPython, so files only change in disk mode
- Check an install from the badge's side after the eject (`.venv/bin/python tools/badge_check.py files`), not by reading the mounted drive: the computer holds writes in its cache until the eject

Read hardware and runtime behaviour from the firmware source in `vendor/tufty2350` and `vendor/badger2350` (both pinned to `v3.1.1`), not only from badgewa.re/docs: the docs can lag the source. Keep `game/` and `saving/record.py` free of Badgeware names so they stay testable on a desktop; `saving/store.py` is the only file that touches `State`.
