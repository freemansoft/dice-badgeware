// Run the Dice Roller in a badgeware-wasm build under Node, press a sequence
// of buttons, and write a frame after each step as JSON.
//
//   node sim/run_headless.mjs [--model tufty] --steps "B,UP:1200" --frames out.json
//
// Run python3 sim/stage.py first. Steps are comma-separated NAME or NAME:ms
// (hold time, default 150 ms); NAME is A, B, C, UP, DOWN or HOME; an empty
// string means no steps. frames[0] is the latest frame SETTLE_MS after the
// first frame; frames[i] the latest frame SETTLE_MS after step i is let go.
// Each frame is width*height*3 bytes, R G B per pixel, row by row. "log" holds
// the app's stdout/stderr lines (the firmware prints "- ERROR:" on a crash).

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SIM = join(dirname(fileURLToPath(import.meta.url)), "dist");
const BUTTON = { HOME: 0x20, A: 0x10, B: 0x08, C: 0x04, UP: 0x02, DOWN: 0x01 };
const MODELS = ["tufty"];
const VBUS_DETECT = 12;
const RTC_ALARM = 13;
const TIMEOUT_MS = 60_000;
const SETTLE_MS = 500;
const DEFAULT_HOLD_MS = 150;

const args = process.argv.slice(2);
const option = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const model = option("--model") || "tufty";
const stepsArg = option("--steps");
const framesPath = option("--frames");

function parseSteps(text) {
  if (!text) return [];
  return text.split(",").map((token) => {
    const [name, ms] = token.trim().split(":");
    if (!(name in BUTTON)) throw new Error("unknown button " + name);
    return { name, hold: ms ? Number(ms) : DEFAULT_HOLD_MS };
  });
}

let steps;
try {
  steps = parseSteps(stepsArg);
} catch (e) {
  console.error(String(e));
  process.exit(2);
}
if (!MODELS.includes(model) || stepsArg === undefined || !framesPath) {
  console.error("usage: node sim/run_headless.mjs [--model tufty] --steps \"A,B:1000\" --frames <out.json>");
  process.exit(2);
}
const DIST = join(SIM, model);

let latest = null;
let count = 0;
let size = { width: 0, height: 0 };
let buttons = 0;
const frames = [];
const log = [];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

globalThis.blitrgba = (addr, w, h) => {
  const heap = globalThis.Module.HEAPU8;
  const rgb = new Array(w * h * 3);
  for (let i = 0; i < w * h; i++) {
    const p = addr + i * 4;
    rgb[i * 3] = heap[p];
    rgb[i * 3 + 1] = heap[p + 1];
    rgb[i * 3 + 2] = heap[p + 2];
  }
  latest = rgb;
  count += 1;
  size = { width: w, height: h };
};
globalThis.backlight = () => {};
globalThis.sim_buttons = () => buttons;
globalThis.sim_gpio_get = (gpio) => (gpio === VBUS_DETECT || gpio === RTC_ALARM ? 1 : null);

function finish(status, code) {
  writeFileSync(framesPath, JSON.stringify({ status, ...size, frames, log }));
  process.exit(code);
}

const { loadMicroPython } = await import(join(DIST, "micropython.mjs"));
const mp = await loadMicroPython({
  url: join(DIST, "micropython.wasm"),
  heapsize: 8 * 1024 * 1024,
  stdout: (line) => { log.push(line); console.log(line); },
  stderr: (line) => { log.push(line); console.error(line); },
});

const manifest = JSON.parse(readFileSync(join(DIST, "fs", "manifest.json"), "utf8"));
for (const [devicePath, local] of manifest) {
  mp.FS.mkdirTree(dirname(devicePath));
  mp.FS.writeFile(devicePath, readFileSync(join(DIST, "fs", local)));
}

const deadline = Date.now() + TIMEOUT_MS;
mp.runPythonAsync(readFileSync(join(DIST, "boot.py"), "utf8")).then(
  () => finish("app exited", 1),
  (error) => { log.push(String(error)); finish("error: " + error, 1); },
);

while (count < 1) {
  if (Date.now() > deadline) finish("timeout waiting for the first frame", 1);
  await sleep(20);
}
await sleep(SETTLE_MS);
frames.push(latest);

for (const step of steps) {
  buttons = BUTTON[step.name];
  await sleep(step.hold);
  buttons = 0;
  const before = count;
  await sleep(SETTLE_MS);
  if (count <= before) finish("no frame after " + step.name, 1);
  frames.push(latest);
}
finish("ok", 0);
