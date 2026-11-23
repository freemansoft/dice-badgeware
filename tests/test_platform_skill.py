"""The project skills: frontmatter, that every firmware file the
badgeware-platforms skill cites as evidence exists in the pinned
submodules, and that the commands and files badge-verify names exist.
(Adapted from freemansoft/MoodBadger2350.)"""

import re

import pytest
from conftest import ROOT

SKILLS = ROOT / ".claude" / "skills"
PLATFORMS = SKILLS / "badgeware-platforms" / "SKILL.md"
VERIFY = SKILLS / "badge-verify" / "SKILL.md"


@pytest.mark.parametrize("name", [
    "badge-deploy", "badge-firmware", "badge-verify", "badgeware-platforms", "dice-docs"])
def test_skill_has_frontmatter_name_and_description(name):
    text = (SKILLS / name / "SKILL.md").read_text()
    assert text.startswith("---\nname: {}\ndescription: ".format(name))


def test_every_vendor_path_cited_in_the_platform_skill_exists():
    cited = set(re.findall(r"vendor/(?:badger2350|tufty2350)/[\w./-]+", PLATFORMS.read_text()))
    assert cited, "the skill must cite firmware source"
    missing = [p for p in sorted(cited) if not (ROOT / p.rstrip(".")).exists()]
    assert missing == []


def test_every_app_path_cited_in_the_platform_skill_exists():
    text = PLATFORMS.read_text()
    cited = set(re.findall(r"`((?:devices|game|saving)/[\w/]+\.py)`", text))
    assert {"devices/tufty.py", "devices/badger.py", "game/controls.py"} <= cited
    missing = [p for p in sorted(cited) if not (ROOT / "apps" / "dice_roller" / p).exists()]
    assert missing == []


def test_both_submodules_are_pinned_to_v3_1_1():
    gitmodules = (ROOT / ".gitmodules").read_text()
    for model in ("tufty", "badger"):
        assert (ROOT / "vendor" / "{}2350".format(model) / "firmware" / "main.py").exists()
        assert "{}2350".format(model) in gitmodules
    assert "v3.1.1" in PLATFORMS.read_text()


def test_other_skills_and_claude_md_point_to_it():
    for path in (ROOT / "CLAUDE.md", SKILLS / "badge-deploy" / "SKILL.md",
                 SKILLS / "badge-firmware" / "SKILL.md", VERIFY):
        assert "badgeware-platforms" in path.read_text(), path


# --- badge-verify: the test and verification process ------------------------

def test_verify_skill_commands_and_files_exist():
    text = VERIFY.read_text()
    tools = set(re.findall(r"tools/(\w+)\.py", text))
    assert tools >= {"badge_info", "badge_check", "update_sim"}
    assert all((ROOT / "tools" / (t + ".py")).exists() for t in tools), tools
    assert "badge-deploy" in text, "installs are handed to the badge-deploy skill"
    for path in ("tests/test_sim.py", "tests/test_sim_badger.py", "tests/simrun.py",
                 "sim/stage.py", "sim/run_headless.mjs", "vendor/tufty2350/ci/ruff.toml"):
        assert path in text and (ROOT / path).exists(), path
    tests = set(re.findall(r"`?(test_\w+\.py)", text))
    missing = [t for t in sorted(tests) if not (ROOT / "tests" / t).exists()]
    assert missing == []


def test_deploy_skill_checks_firmware_then_the_copy_after_the_eject():
    text = (SKILLS / "badge-deploy" / "SKILL.md").read_text()
    firmware, install, check = (text.index(s) for s in (
        "tools/badge_info.py", 'tools/install.py" --dest', 'tools/badge_check.py" files'))
    assert firmware < install < check
    assert "OLDER" in text and "badge-firmware" in text and "disk mode" in text


def test_skills_are_pointed_to_from_the_docs():
    claude = (ROOT / "CLAUDE.md").read_text()
    readme = (ROOT / "README.md").read_text()
    for name in ("badge-deploy", "badge-firmware", "badge-verify", "badgeware-platforms",
                 "dice-docs"):
        assert name in claude and name in readme, name
