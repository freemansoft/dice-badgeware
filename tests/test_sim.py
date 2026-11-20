"""Run the real app in the badgeware-wasm simulator (Node) and check pixels.

Pixel positions and colours come from apps/dice_roller/display_tufty.py:
die bodies are bright palette colours (grey > 90), locked bodies dark
(< 70), background very dark (< 30); the header at (4, 4) is dark on the
roll screen (< 50) and blue on the configure screen (> 70).
"""

import json
import shutil
import subprocess
import sys

import dice_layout
import pytest
from conftest import ROOT

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

WIDTH = 320


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    subprocess.run([sys.executable, "sim/stage.py"], cwd=ROOT, check=True, capture_output=True)
    out_dir = tmp_path_factory.mktemp("sim")

    def _run(steps):
        out = out_dir / "frames.json"
        subprocess.run(
            ["node", "sim/run_headless.mjs", "--model", "tufty", "--steps", steps, "--frames", str(out)],
            cwd=ROOT, check=False, capture_output=True, timeout=120,
        )
        return json.loads(out.read_text())

    return _run


def grey(frame, x, y):
    return frame[y * WIDTH + x]


def probe(count, i):
    cx, cy, half = dice_layout.grid_slots(320, 240, count)[i]
    return cx - half + 8, cy - half + 8


def no_errors(result):
    return result["status"] == "ok" and not any("- ERROR" in line for line in result["log"])


def test_boots_to_four_dice_two_by_two(run):
    r = run("")
    f = r["frames"][0]
    assert no_errors(r), r["log"]
    assert (r["width"], r["height"]) == (320, 240)
    assert all(grey(f, *probe(4, i)) > 90 for i in range(4))
    assert grey(f, *probe(6, 0)) < 30
    assert grey(f, 4, 4) < 50


def test_b_opens_configure_and_b_returns(run):
    r = run("B,B")
    _, f1, f2 = r["frames"]
    assert no_errors(r), r["log"]
    assert grey(f1, 4, 4) > 70
    assert grey(f2, 4, 4) < 50


def test_up_locks_highlighted_die(run):
    r = run("UP")
    f1 = r["frames"][1]
    assert grey(f1, *probe(4, 0)) < 70
    assert grey(f1, *probe(4, 1)) > 90


def test_long_up_unlocks_all(run):
    frames = run("UP,C,UP,UP:1200")["frames"]
    assert grey(frames[3], *probe(4, 0)) < 70
    assert grey(frames[3], *probe(4, 1)) < 70
    assert grey(frames[4], *probe(4, 0)) > 90
    assert grey(frames[4], *probe(4, 1)) > 90


def test_configure_five_dice(run):
    r = run("B,UP,B")
    f = r["frames"][-1]
    assert no_errors(r), r["log"]
    assert all(grey(f, *probe(5, i)) > 90 for i in range(5))


def test_rolling_does_not_error(run):
    assert no_errors(run("DOWN,DOWN,DOWN"))
