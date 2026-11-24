"""The README, CLAUDE.md and the project skills stay true to the repo:
every skill has the frontmatter Claude Code loads it by, every repo path
they cite exists (the badgeware-platforms skill's vendor/ evidence
included), and the firmware version they call pinned is the one
sim/wasm/VERSION.json pins. (Adapted from freemansoft/MoodBadger2350.)"""

import json
import re

import pytest
from conftest import ROOT

SKILLS = ROOT / ".claude" / "skills"
PLATFORMS = SKILLS / "badgeware-platforms" / "SKILL.md"
DOCS = [ROOT / "README.md", ROOT / "CLAUDE.md", *sorted(SKILLS.glob("*/SKILL.md"))]

# A path from the repository root, not preceded by another path segment
# (so /system/apps/... on the badge isn't one). sim/dist is built by
# sim/stage.py and not committed.
REPO_PATH = re.compile(r"(?<![\w./<-])((?:apps|tools|tests|sim|vendor|\.githooks|\.github)/[\w./-]*\w)")
NOT_COMMITTED = ("sim/dist",)


@pytest.mark.parametrize("skill", sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md")))
def test_skill_has_frontmatter_name_and_description(skill):
    text = (SKILLS / skill / "SKILL.md").read_text()
    assert text.startswith("---\nname: {}\ndescription: ".format(skill))


def test_every_repo_path_the_docs_cite_exists():
    missing = []
    for doc in DOCS:
        text = doc.read_text()
        for path in sorted(set(REPO_PATH.findall(text))):
            if not path.startswith(NOT_COMMITTED) and not (ROOT / path).exists():
                missing.append("{}: {}".format(doc.relative_to(ROOT), path))
        # test files named on their own, as in badge-verify's list
        for name in sorted(set(re.findall(r"`(test_\w+\.py)`", text))):
            if not list((ROOT / "tests").rglob(name)):
                missing.append("{}: {}".format(doc.relative_to(ROOT), name))
    assert any("vendor/" in p for p in REPO_PATH.findall(PLATFORMS.read_text())), \
        "the platform skill must cite firmware source"
    assert missing == []


def test_every_app_path_cited_in_the_platform_skill_exists():
    text = PLATFORMS.read_text()
    cited = set(re.findall(r"`((?:devices|game|saving)/[\w/]+\.py)`", text))
    assert {"devices/tufty.py", "devices/badger.py", "game/controls.py"} <= cited
    missing = [p for p in sorted(cited) if not (ROOT / "apps" / "dice_roller" / p).exists()]
    assert missing == []


def test_docs_name_the_pinned_firmware_version():
    # sim/wasm/VERSION.json records the tag tools/update_sim.py checked the
    # vendor/ submodules out at. Pre-release tags (v4.0.0-ide.1) are only
    # examples in the docs, so they don't count.
    pinned = set(json.loads((ROOT / "sim" / "wasm" / "VERSION.json").read_text())["firmware"].values())
    assert len(pinned) == 1, pinned
    named = {}
    for doc in DOCS:
        for version in re.findall(r"\bv\d+\.\d+\.\d+\b(?![-.\w])", doc.read_text()):
            named.setdefault(version, []).append(doc.relative_to(ROOT).as_posix())
    assert set(named) == pinned, named
