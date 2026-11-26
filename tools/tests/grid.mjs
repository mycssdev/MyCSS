// Grid system stress test: runs the self-test built into dist/grid-spec.html.
// 25 stages x 16 widths x 5 modes (default, compact, spacious, RTL, long
// content); fails on any overflow, spill, wrong column count for the active
// container size, or a knob leaking into a nested grid.
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";

const page_ = resolve(dirname(fileURLToPath(import.meta.url)), "../../packages/design/dist/grid-spec.html");
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" }).catch(() => chromium.launch());
const page = await browser.newPage({ viewport: { width: 1360, height: 900 } });
const errors = [];
page.on("pageerror", e => errors.push(e.message));
await page.goto("file://" + page_.replace(/\\/g, "/") + "#selftest");
await page.waitForFunction(() => window.__selftest, null, { timeout: 120000 });
const r = await page.evaluate(() => window.__selftest);
await browser.close();

console.log(r.text.split("\n").filter((l, i) => i !== 1).join("\n"));
if (errors.length) console.log("page errors:", errors);
if (r.verdict !== "PASS" || errors.length) { console.error("\nGRID: FAIL"); process.exit(1); }
console.log("\nGRID: all checks passed");
