"""ruff.toml can extend only one of Pimoroni's two rule files. The app
runs on both badges, so the two must say the same thing: if a firmware
update makes them differ, this fails and someone decides which rules to
follow (see ruff.toml)."""

import tomllib

from conftest import ROOT

VENDOR_RULES = ["vendor/tufty2350/ci/ruff.toml", "vendor/badger2350/ci/ruff.toml"]


def rules(path):
    with open(ROOT / path, "rb") as f:
        return tomllib.load(f)


def test_tufty_and_badger_lint_rules_match():
    tufty, badger = (rules(p) for p in VENDOR_RULES)
    assert tufty == badger


def test_ruff_toml_extends_pimoronis_rules():
    assert rules("ruff.toml")["extend"] in VENDOR_RULES
