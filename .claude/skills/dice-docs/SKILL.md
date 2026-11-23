---
name: dice-docs
description: Writing and formatting standard for the Dice Roller's Markdown (README.md, CLAUDE.md, the skill files in .claude/skills, and the designs and plans in docs/superpowers). Use whenever you create or edit any .md file in this repo, and before every commit that includes Markdown, since the pre-commit hook and CI reject unformatted files. Covers prettier (the version in .prettier-version), wrapping, tables, tone and spelling, which doc owns which topic, link anchors, and the tests that pin doc content.
---

# Dice Roller documentation standard

(Adapted from freemansoft/claude-buddy-badgeware.)

## Formatting: prettier, pinned

All Markdown is formatted with prettier at the version in
`.prettier-version`, settings in `.prettierrc.json`
(`proseWrap: preserve`). The version is pinned in that one file so
everyone's tables and lists come out byte-identical; an unpinned
`npx prettier` can reformat files nobody touched.

After editing Markdown, and before committing:

```bash
npx --yes prettier@$(cat .prettier-version) --config .prettierrc.json --write <changed .md files>
git ls-files -z '*.md' | xargs -0 npx --yes prettier@$(cat .prettier-version) --config .prettierrc.json --check
```

`git ls-files` only lists tracked files, so check a new `.md` file by
name too. `.githooks/pre-commit` checks the staged `.md` files (and
lints staged Python) and blocks the commit if any fail; CI runs the
same check on every tracked `.md`. The hook is active when
`git config core.hooksPath` prints `.githooks`; if it doesn't, tell
the user rather than setting it silently. Don't bypass the hook with
`--no-verify`; format the files instead.

To change the prettier version, change `.prettier-version` only. The
hook, CI and every doc read or name that file; never write the version
number anywhere else (`tests/project/test_prettier_version.py` fails
if a file hard-codes it).

## Wrapping and layout

`proseWrap: preserve` means prettier won't rewrap prose, so wrap by
hand:

- Prose and list items at about **72 columns**. Continuation lines of a
  list item are indented to the item's text.
- Tables are never wrapped; prettier aligns them. Keep cells short
  enough to read, and move long explanations into prose below.
- Code, commands, buttons' key names and file paths in backticks. Shell
  blocks are `sh` or `bash`; JSON examples are `json`.
- Button names as the badge prints them: A, B, C, UP, DOWN, HOME, BOOT,
  RESET. Screen titles in bold (**Roll Baby Roll**, **Setup**).

## Tone and spelling

The docs are written in plain, short sentences for someone who owns a
badge, not someone who wrote this code.

- British spelling (_colour_, _licence_, _behaviour_), matching the
  existing docs.
- Say what happens, with the number: "sleeps after 30 seconds without
  a press", not "sleeps after a while".
- Be honest about what's unverified: anything only read from the
  firmware source, or not yet tried on a badge, says so.
- Explain why, briefly, when a choice isn't obvious.
- Run commands the way the repo does: `.venv/bin/pytest`,
  `.venv/bin/ruff`, `python3 tools/install.py`, and
  `.venv/bin/python tools/badge_info.py` for the tools that need
  `mpremote`.

## Which doc owns what

Each topic has one home. Other docs link to it instead of copying it,
so they can't drift apart.

| Topic                                                         | Home                                                    |
| ------------------------------------------------------------- | ------------------------------------------------------- |
| What the app does, buttons, saved setup, Badger notes         | `README.md`                                             |
| Installing, the firmware check before it, the badge tools     | `README.md` "Install"; `badge-deploy` skill for Claude  |
| Checking and flashing firmware                                | `badge-firmware` skill; `README.md` "Install" in short  |
| Development set-up, commands, CI, the hook, layout, simulator | `README.md` "Development"; `CLAUDE.md` in short         |
| Adding a badge                                                | `README.md` "Adding a badge"                            |
| Badger vs Tufty firmware differences, the app's rules         | `badgeware-platforms` skill                             |
| Test layers and hand checklists for each badge                | `badge-verify` skill                                    |
| Markdown standard                                             | this skill                                              |
| Why a feature was designed as it was, and its plan            | `docs/superpowers/specs/` and `docs/superpowers/plans/` |

The designs and plans in `docs/superpowers/` are dated records of what
was decided at the time. Don't rewrite them to match later changes;
write a new design or plan instead, and update the README.

When you change a number (a timeout, a limit, a size), grep the docs
for the old value and the constant's name: some numbers appear in more
than one place on purpose, as summaries.

## Links and anchors

- Link between docs with relative paths; link within the README with
  `#anchors`.
- Renaming a heading changes its anchor. Before renaming, grep the
  repo for `#<old-anchor>` and fix every link.
  `tests/project/test_readme.py` fails if a README `#anchor` link
  doesn't resolve.
- `tests/project/test_docs.py` fails if a repo path that the README,
  `CLAUDE.md` or a skill cites (`tools/...`, `tests/...`,
  `vendor/...`) no longer exists, or if they name a firmware version
  other than the one `sim/wasm/VERSION.json` pins.
