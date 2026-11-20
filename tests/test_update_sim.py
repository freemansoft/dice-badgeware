import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import update_sim

RUNS = [
    {"databaseId": 1, "headSha": "a", "headBranch": "main", "workflowName": "build", "conclusion": "success", "createdAt": "2026-09-11T00:00:00Z"},
    {"databaseId": 2, "headSha": "b", "headBranch": "v3.1.0", "workflowName": "build", "conclusion": "success", "createdAt": "2026-09-24T00:00:00Z"},
    {"databaseId": 3, "headSha": "c", "headBranch": "main", "workflowName": "build", "conclusion": "failure", "createdAt": "2026-09-25T00:00:00Z"},
    {"databaseId": 4, "headSha": "d", "headBranch": "main", "workflowName": "build", "conclusion": "success", "createdAt": "2026-09-23T00:00:00Z"},
]
RELEASES = [
    {"tagName": "v4.0.0-ide.1", "isPrerelease": True, "isDraft": False, "publishedAt": "2026-10-05T00:00:00Z"},
    {"tagName": "v3.1.1", "isPrerelease": False, "isDraft": False, "publishedAt": "2026-09-23T00:00:00Z"},
    {"tagName": "v3.1.0", "isPrerelease": False, "isDraft": False, "publishedAt": "2026-09-14T00:00:00Z"},
]


def test_latest_build_run():
    assert update_sim.latest_build_run(RUNS)["databaseId"] == 4


def test_latest_build_run_none():
    assert update_sim.latest_build_run([]) is None


def test_latest_release_tag():
    assert update_sim.latest_release_tag(RELEASES) == "v3.1.1"


def test_artifact_name():
    assert update_sim.artifact_name("tufty") == "badgeware-tufty2350-asyncify"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A temp repo root pinned to run 1 / v3.1.1, with gh and git stubbed."""
    wasm = tmp_path / "sim" / "wasm"
    (wasm / "tufty").mkdir(parents=True)
    (wasm / "tufty" / "micropython.mjs").write_text("old mjs")
    (wasm / "tufty" / "micropython.wasm").write_text("old wasm")
    (tmp_path / "vendor" / "tufty2350").mkdir(parents=True)
    pin(tmp_path, 1)
    monkeypatch.setattr(update_sim, "ROOT", tmp_path)
    monkeypatch.setattr(update_sim, "gh_ready", lambda: True)
    monkeypatch.setattr(update_sim, "gh_json", lambda args: RUNS if args[0] == "run" else RELEASES)
    git_calls = []
    monkeypatch.setattr(update_sim, "git", git_calls.append)
    return SimpleNamespace(root=tmp_path, git_calls=git_calls)


def pin(root, run_id):
    version = {
        "wasm": {"repo": "pimoroni/badgeware-wasm", "commit": "x", "run_id": run_id, "date": "2026-09-11"},
        "firmware": {"tufty": "v3.1.1"},
    }
    (root / "sim" / "wasm" / "VERSION.json").write_text(json.dumps(version))


def snapshot(root):
    wasm = root / "sim" / "wasm"
    return {p.relative_to(wasm).as_posix(): p.read_bytes() for p in sorted(wasm.rglob("*")) if p.is_file()}


def test_check_current_returns_0(repo):
    pin(repo.root, 4)
    assert update_sim.main(["--check"]) == 0


def test_check_newer_returns_1(repo, capsys):
    assert update_sim.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "run 1" in out and "run 4" in out


def test_download_missing_files_changes_nothing(repo, monkeypatch):
    before = snapshot(repo.root)
    monkeypatch.setattr(update_sim, "gh_run", lambda args: None)
    assert update_sim.main([]) == 1
    assert snapshot(repo.root) == before
    assert repo.git_calls == []


def test_update_replaces_build_and_writes_version(repo, monkeypatch):
    def fake_download(args):
        dest = Path(args[args.index("-D") + 1])
        (dest / "micropython.mjs").write_text("new mjs")
        (dest / "micropython.wasm").write_text("new wasm")

    monkeypatch.setattr(update_sim, "gh_run", fake_download)
    assert update_sim.main([]) == 0
    files = snapshot(repo.root)
    assert files["tufty/micropython.mjs"] == b"new mjs"
    version = json.loads(files["VERSION.json"])
    assert version["wasm"]["run_id"] == 4 and version["wasm"]["commit"] == "d"
    assert version["wasm"]["date"] == "2026-09-23" and version["firmware"] == {"tufty": "v3.1.1"}
    assert ["-C", str(repo.root / "vendor" / "tufty2350"), "checkout", "-q", "v3.1.1"] in repo.git_calls
