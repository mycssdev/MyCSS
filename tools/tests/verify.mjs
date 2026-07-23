import { chromium } from "playwright";

const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" }).catch(() => chromium.launch());
const page = await browser.newPage({ viewport: { width: 1360, height: 900 } });
page.on("console", m => { if (m.type() === "error") console.log("CONSOLE ERROR:", m.text()); });
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";
const demo = resolve(dirname(fileURLToPath(import.meta.url)), "../../packages/design/dist/demo.html");
await page.goto("file://" + demo.replace(/\\/g, "/"));
await page.waitForTimeout(300);

const probe = () => page.evaluate(() => {
  const cs = el => getComputedStyle(el);
  return {
    h1Size: cs(document.querySelector(".u-h1")).fontSize,
    bodyBg: cs(document.body).backgroundColor,
    btnBg: cs(document.querySelector(".my-button")).backgroundColor,
    jadeBtnBg: cs(document.querySelector('[data-accent="jade"] .my-button')).backgroundColor,
    cardInset: cs(document.querySelector(".my-card")).paddingTop,
    regionMd: cs(document.querySelector("main section")).paddingTop,
    featuredBorder: cs(document.querySelector('.my-card[data-variant="featured"]')).borderTopColor,
    plainBorder: cs(document.querySelector('.my-card:not([data-variant])')).borderTopColor,
    disabledBtnBg: cs(document.querySelector('.my-button[data-state="disabled"]')).backgroundColor,
  };
});

const compositions = () => page.evaluate(() => {
  const cs = el => getComputedStyle(el);
  // bare c-stack (no utility) should default to stack-md
  const t = document.createElement("div");
  t.className = "c-stack";
  document.body.appendChild(t);
  const stackGap = cs(t).rowGap;
  t.remove();
  const sw = document.getElementById("switcher-demo").children;
  const grid = document.getElementById("grid-demo").children;
  const side = document.getElementById("sidebar-demo").children;
  return {
    stackGap,
    switcherSameRow: sw[0].offsetTop === sw[2].offsetTop,
    gridCols: new Set([...grid].map(c => c.offsetLeft)).size,
    sidebarSameRow: side[0].offsetTop === side[1].offsetTop,
    sidebarContentWider: side[1].offsetWidth > side[0].offsetWidth,
  };
});

const results = {};
results.light = await probe();
results.comp_wide = await compositions();

await page.setViewportSize({ width: 480, height: 900 });
await page.waitForTimeout(200);
results.comp_narrow = await compositions();
await page.screenshot({ path: "demo-narrow.png" });
await page.setViewportSize({ width: 1360, height: 900 });
await page.waitForTimeout(200);

await page.evaluate(() => document.documentElement.dataset.density = "compact");
results.compact = await probe();
await page.evaluate(() => document.documentElement.dataset.density = "spacious");
results.spacious = await probe();
await page.evaluate(() => { document.documentElement.dataset.density = "comfortable"; document.documentElement.dataset.mode = "dark"; });
results.dark = await probe();
await page.evaluate(() => document.documentElement.dataset.accent = "iris");
results.dark_iris = await probe();

// subtree theming — reset page to light/comfortable first
await page.evaluate(() => { const r = document.documentElement.dataset; r.mode = "light"; r.accent = "brand"; r.density = "comfortable"; });
results.subtree = await page.evaluate(() => {
  const cs = el => getComputedStyle(el);
  const host = document.createElement("div");
  host.innerHTML = `
    <div data-mode="dark"><p id="t-dark-p" class="u-bg-neutral-primary">x</p></div>
    <div data-density="compact"><span id="t-compact-h" class="u-h1">x</span></div>`;
  document.body.appendChild(host);
  const out = {
    darkSubtreeBg: cs(document.getElementById("t-dark-p")).backgroundColor,
    compactSubtreeH1: cs(document.getElementById("t-compact-h")).fontSize,
    pageBg: cs(document.body).backgroundColor,
    pageH1: cs(document.querySelector(".u-h1")).fontSize,
  };
  host.remove();
  return out;
});

console.log(JSON.stringify(results, null, 1));

await page.evaluate(() => { const r = document.documentElement.dataset; r.mode = "light"; r.accent = "brand"; r.density = "comfortable"; });
await page.waitForTimeout(200);
await page.screenshot({ path: "demo-light.png" });
await page.evaluate(() => { const r = document.documentElement.dataset; r.mode = "dark"; r.accent = "iris"; });
await page.waitForTimeout(200);
await page.screenshot({ path: "demo-dark.png" });

const px = s => parseFloat(s);
let failures = 0;
const assert = (name, cond) => { console.log(cond ? `PASS ${name}` : `FAIL ${name}`); if (!cond) failures++; };
// tokens + themes (regression)
assert("h1 49px comfortable", results.light.h1Size === "49px");
assert("h1 compact 35px", px(results.compact.h1Size) === 35);
assert("h1 spacious 76px", px(results.spacious.h1Size) === 76);
assert("card inset shrinks in compact", px(results.compact.cardInset) < px(results.light.cardInset));
assert("region grows in spacious", px(results.spacious.regionMd) > px(results.light.regionMd));
assert("body bg flips in dark", results.dark.bodyBg !== results.light.bodyBg);
assert("brand solid rebeccapurple", results.light.btnBg === "rgb(102, 51, 153)");
assert("accent swap changes button", results.dark_iris.btnBg !== results.dark.btnBg);
assert("jade subtree differs", results.light.jadeBtnBg !== results.light.btnBg);
assert("dark subtree in light page", results.subtree.darkSubtreeBg !== results.subtree.pageBg);
assert("compact subtree h1 35px", results.subtree.compactSubtreeH1 === "35px" && results.subtree.pageH1 === "49px");
// exceptions grammar
assert("data-variant=featured changes card border", results.light.featuredBorder !== results.light.plainBorder);
assert("data-state=disabled changes button", results.light.disabledBtnBg !== results.light.btnBg);
// compositions
assert("c-stack default gap = stack-md 16px", results.comp_wide.stackGap === "16px");
assert("c-switcher row when wide", results.comp_wide.switcherSameRow === true);
assert("c-switcher column when narrow", results.comp_narrow.switcherSameRow === false);
assert("c-grid multi-column wide", results.comp_wide.gridCols > 1);
assert("c-grid single column narrow", results.comp_narrow.gridCols === 1);
assert("c-sidebar side-by-side wide", results.comp_wide.sidebarSameRow === true && results.comp_wide.sidebarContentWider === true);
assert("c-sidebar folds narrow", results.comp_narrow.sidebarSameRow === false);

await browser.close();
process.exit(failures ? 1 : 0);
