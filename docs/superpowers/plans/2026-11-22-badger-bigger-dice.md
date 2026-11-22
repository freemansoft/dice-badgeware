# Bigger Badger Dice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Badger dice fill their 54 px slot; a locked die is light grey all over.

**Architecture:** Only `apps/dice_roller/devices/badger.py` draws differently; the layout (`game/layout.py`) and the Tufty are untouched. Pixels are proved in the Badger simulator tests.

**Tech Stack:** MicroPython (Badgeware v3.1.1), pytest, badgeware-wasm simulator under Node.

**Spec:** `docs/superpowers/specs/2026-11-22-badger-bigger-dice-design.md`

## Global Constraints

- Shades: BLACK (0,0,0), DARK (96,96,96), LIGHT (160,160,160), WHITE (255,255,255) only.
- Die: 2 × `half` across, black 2 px outline; unlocked face white, locked face LIGHT; number and "dN" black.
- Highlight ring: black, 3 px wide, outer edge `half + 4`.
- Sizes: SIZE_VALUE 29, SIZE_TYPE 10, SIZE_FACES 19.
- Tufty unchanged.

## Review Focus

- The highlight ring on a top-row die must not merge into the title bar (title bar ends at y 21; ring starts at y 23).
- The ring on a bottom-row die must clear the divider at BAR_TOP 151.
- The "d6" label must stay inside the die's face at the bigger size.
- Setup-screen dice (never locked) stay white.

---

### Task 1: Full-size dice, grey when locked

**Files:**

- Modify: `apps/dice_roller/devices/badger.py` (die constants, `_die`, sizes, `_draw_roll` label position)
- Modify: `tests/test_sim_badger.py`
- Modify: `README.md:27-28`, `docs/superpowers/specs/2026-11-20-badger-and-saved-roll-design.md` (Look table, pointer to the new spec)

**Interfaces:**

- Produces: `badger.LOCK_INSET` and `badger.BODY_INSET` removed; `_die(cx, cy, half, highlighted, locked)` keeps its signature and returns the face's half-size.

- [ ] **Step 1: Change the simulator tests first**
  - `body_shade(frame, i)` probes inside the die near its left edge (`cx - half + 6`, `cy + half // 2`); `box_shade` and `test_badger_lock_box_is_wide` go.
  - `test_badger_boots_to_four_white_dice`: all four faces "white".
  - `test_badger_lock_draws_grey_box` → `test_badger_locked_die_is_grey`: die 1 face "light", die 2 "white".
  - `test_badger_long_up_unlocks_all`: frame 2 die 1 "light"; frame 3 all "white".
  - New `test_badger_dice_are_large`: on frame 0, the black outline's row through die 1's centre spans ≥ 50 px.
  - New `test_badger_highlight_clears_the_bars`: on frame 0, row 22 at die 1's x is white (gap under the title bar), and row BAR_TOP - 1 at the bottom-left die's x is white.

- [ ] **Step 2: Run them, watch the look tests fail**

Run: `.venv/bin/pytest tests/test_sim_badger.py -q`
Expected: FAIL in `test_badger_locked_die_is_grey`, `test_badger_dice_are_large`, `test_badger_long_up_unlocks_all` (and the probe-based ones) on today's 38 px die.

- [ ] **Step 3: Draw the dice**
  - Drop LOCK_INSET / BODY_INSET; the die body is `half`; face fill is LIGHT when locked, else WHITE.
  - Sizes from Global Constraints; "dN" at `cy + half - 10`.

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 5: Docs, then commit**

README: "a locked die turns grey". Old spec: Look table's Locked row points to the new spec.

```bash
git add -A && git commit -m "Badger: dice fill their slot; a locked die turns grey"
```
