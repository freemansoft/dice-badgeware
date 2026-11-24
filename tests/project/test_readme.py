"""The README's internal #anchor links point at real headings.
(Adapted from freemansoft/MoodBadger2350.)"""

import re

from conftest import ROOT

README = ROOT / "README.md"


def _slug(heading):
    # GitHub's heading anchors: lower case, punctuation dropped, spaces to hyphens.
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def test_readme_internal_links_resolve():
    text = README.read_text()
    anchors = {_slug(h) for h in re.findall(r"^#+ (.+)$", text, re.MULTILINE)}
    links = set(re.findall(r"\]\(#([\w-]+)\)", text))
    assert links, "the README links to its own sections"
    assert links <= anchors, links - anchors
