"""Run the app in the badgeware-wasm simulator (sim/run_headless.mjs).

Shared by the Tufty and Badger simulator tests. stage() builds sim/dist
once per test session; simulate() boots one model, presses the steps and
returns the parsed output (frames, refreshes per step, saved state, log).
"""

import json
import shutil
import subprocess
import sys

import pytest
from conftest import ROOT

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

_staged = []


def stage():
    if not _staged:
        subprocess.run([sys.executable, "sim/stage.py"], cwd=ROOT, check=True, capture_output=True)
        _staged.append(True)


def no_errors(result):
    return result["status"] == "ok" and not any("- ERROR" in line for line in result["log"])


def simulate(model, steps, out_path, state_path=None):
    """Boot `model`, press `steps` ("A,UP:1200", or "" for none) and return
    the output. Each call writes its own out_path, so a run that dies before
    writing can't be mistaken for an earlier run's frames."""
    stage()
    command = ["node", "sim/run_headless.mjs", "--model", model, "--steps", steps, "--frames", str(out_path)]
    if state_path is not None:
        command += ["--state", str(state_path)]
    done = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True, timeout=120)
    assert out_path.exists(), done.stderr
    result = json.loads(out_path.read_text())
    assert no_errors(result), (result["status"], result["log"])
    assert len(result["frames"]) == 1 + (len(steps.split(",")) if steps else 0)
    return result
