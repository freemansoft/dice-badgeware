"""Stage a servable simulator site in sim/dist (not committed).

sim/dist/<model>/ holds the host page, that badge's badgeware-wasm build
(sim/wasm/<model>/, fetched by tools/update_sim.py), boot.py, and fs/:
every file the host writes into the simulated badge's filesystem, listed
in fs/manifest.json as [device path, file under fs/] pairs.
sim/dist/index.html links to each model.

    python3 sim/stage.py
"""

import json
import shutil
from pathlib import Path

SIM = Path(__file__).resolve().parent
ROOT = SIM.parent
DIST = SIM / "dist"
MODELS = ("tufty", "badger")
APP = "dice_roller"

# The firmware imports its own submodules as __import__(".frozen/badgeware/x"),
# which only resolves for frozen modules. MicroPython reads a leading dot in a
# filesystem path as a relative import, so the package is staged at /frozen
# and those imports are rewritten in the staged copies (never in vendor/).
FROZEN_IMPORT = '__import__(".frozen/'
STAGED_IMPORT = '__import__("/frozen/'

LANDING = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dice Roller Simulator</title>
<style>body { font: 16px/1.6 system-ui, sans-serif; margin: 2rem 16px; color: #2b2b2b; background: #fff; }</style>
</head>
<body>
<h1>Dice Roller Simulator</h1>
<ul>
<li><a href="tufty/">Tufty 2350</a> (colour LCD, 320x240)</li>
<li><a href="badger/">Badger 2350</a> (e-ink, 264x176, four greys)</li>
</ul>
</body>
</html>
"""


def trees(model):
    """device directory -> local source directory, for one badge model."""
    firmware = ROOT / "vendor" / (model + "2350")
    return [
        ("/frozen/badgeware", firmware / "modules" / "common" / "badgeware"),
        ("/rom/fonts", firmware / "romfs" / "fonts"),
        ("/system/assets/fonts", firmware / "firmware" / "assets" / "fonts"),
        ("/system/apps/" + APP, ROOT / "apps" / APP),
        ("/lib", SIM / "stubs"),
    ]


def stage(model):
    """Stage sim/dist/<model>/ and return the number of files in its fs/."""
    out = DIST / model
    fs = out / "fs"
    fs.mkdir(parents=True)

    for name in ("micropython.mjs", "micropython.wasm"):
        shutil.copy2(SIM / "wasm" / model / name, out / name)
    shutil.copy2(SIM / "index.html", out / "index.html")
    shutil.copy2(SIM / "boot.py", out / "boot.py")

    manifest = []
    rewrites = 0
    for device_dir, source in trees(model):
        if not source.is_dir():
            raise SystemExit(f"missing {source}; run: git submodule update --init")
        for path in sorted(source.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.name.startswith("."):
                continue
            relative = path.relative_to(source).as_posix()
            local = device_dir.strip("/") + "/" + relative
            (fs / local).parent.mkdir(parents=True, exist_ok=True)
            if device_dir == "/frozen/badgeware" and path.suffix == ".py":
                text = path.read_text()
                rewrites += text.count(FROZEN_IMPORT)
                (fs / local).write_text(text.replace(FROZEN_IMPORT, STAGED_IMPORT))
            else:
                shutil.copy2(path, fs / local)
            manifest.append([device_dir + "/" + relative, local])

    if rewrites == 0:
        raise SystemExit(f"no {FROZEN_IMPORT} imports found; the firmware layout changed")

    (fs / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return len(manifest)


def stage_all():
    if DIST.exists():
        shutil.rmtree(DIST)
    counts = {model: stage(model) for model in MODELS}
    (DIST / "index.html").write_text(LANDING)
    return counts


if __name__ == "__main__":
    for model, count in stage_all().items():
        print(f"staged {count} files in {(DIST / model).relative_to(ROOT)}")
