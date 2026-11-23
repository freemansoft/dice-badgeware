"""The README keeps its key reference links, and its internal #anchor
links point at real headings. (Adapted from freemansoft/MoodBadger2350.)"""

import re

import pytest
from conftest import ROOT

README = ROOT / "README.md"


@pytest.mark.parametrize("required", [
    "https://youtu.be/B9ww5fzRGVs",
    "https://shop.pimoroni.com/products/tufty-2350",
    "https://github.com/pimoroni/tufty2350",
    "https://github.com/pimoroni/badger2350",
    "https://github.com/pimoroni/badgeware-wasm",
    "https://github.com/obra/superpowers-marketplace",
    "https://cli.github.com",
])
def test_readme_contains_reference(required):
    assert required in README.read_text()


def _slug(heading):
    # GitHub's heading anchors: lower case, punctuation dropped, spaces to hyphens.
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def test_readme_internal_links_resolve():
    text = README.read_text()
    anchors = {_slug(h) for h in re.findall(r"^#+ (.+)$", text, re.MULTILINE)}
    links = set(re.findall(r"\]\(#([\w-]+)\)", text))
    assert links, "the README links to its own sections"
    assert links <= anchors, links - anchors


def test_slug_matches_github():
    assert _slug("Adding a badge") == "adding-a-badge"
    assert _slug("Roll screen (where the app starts)") == "roll-screen-where-the-app-starts"


def test_install_checks_firmware_and_the_copy_on_the_badge():
    text = README.read_text()
    install = text[text.index("## Install"):text.index("## Development")]
    for needed in ("tools/badge_info.py", "OLDER", "tools/install.py",
                   "tools/badge_check.py files", "tools/flash_firmware.py", "disk mode"):
        assert needed in install, needed
