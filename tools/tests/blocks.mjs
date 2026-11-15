// Component (BLOCKS) checks: CSS/markup coverage, js/mycss.js behaviours, brand kit reach.
//   node tools/tests/blocks.mjs
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";
import { readFileSync, readdirSync } from "node:fs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const dist = resolve(root, "packages/design/dist");
const url = (p) => "file://" + p.replace(/\\/g, "/");
const results = [];
const check = (name, ok, detail = "") => { results.push(ok); console.log((ok ? "  ok   " : "  FAIL ") + name + (ok || !detail ? "" : "  -> " + detail)); };

// ---------- 1. every .my-* class the specimens use has CSS, and every one the CSS defines is shown
const css = readFileSync(resolve(dist, "css/mycss.css"), "utf8");
const cssClasses = new Set([...css.matchAll(/\.(my-[a-z0-9-]+)/g)].map((m) => m[1]));
const specs = readdirSync(dist).filter((f) => f.endsWith("-spec.html"));
const htmlClasses = new Set();
for (const f of specs) {
  const html = readFileSync(resolve(dist, f), "utf8").replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/g, "");
  for (const m of html.matchAll(/class=(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g))
    for (const c of (m[1] ?? m[2] ?? m[3]).split(/\s+/)) if (c.startsWith("my-")) htmlClasses.add(c);
}
const unstyled = [...htmlClasses].filter((c) => !cssClasses.has(c));
// my-icon: optional hook, same rules as a bare <svg>. my-toast-region: made by MyCSS.toast(), checked below.
const scriptOnly = new Set(["my-icon", "my-toast-region"]);
const unshown = [...cssClasses].filter((c) => !htmlClasses.has(c) && !scriptOnly.has(c));
console.log(`coverage: ${cssClasses.size} classes in mycss.css, ${htmlClasses.size} used across ${specs.length} specimen pages`);
check("every class used in a specimen has a rule", unstyled.length === 0, unstyled.join(", "));
check("every class in the CSS appears in a specimen", unshown.length === 0, unshown.join(", "));

const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" }).catch(() => chromium.launch());
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push(String(e)));

// ---------- 2. specimen pages load clean
for (const f of specs) {
  errors.length = 0;
  await page.goto(url(resolve(dist, f)));
  await page.waitForTimeout(100);
  check(`${f} loads without errors`, errors.length === 0, errors.join(" | "));
}

// ---------- 3. behaviours
errors.length = 0;
await page.goto(url(resolve(root, "tools/tests/fixtures/blocks.html")));
await page.waitForFunction(() => window.MyCSS);
await page.addStyleTag({ content: "*, *::before, *::after { transition: none !important; animation: none !important; }" });
const $ = (sel, fn, arg) => page.$eval(sel, fn, arg);
const panels = () => page.$$eval('[role="tabpanel"]', (ps) => ps.filter((p) => !p.hidden).map((p) => p.id).join());
const selected = () => page.$$eval('#tabs [role="tab"][aria-selected="true"]', (ts) => ts.map((t) => t.id).join());
const focused = () => page.evaluate(() => document.activeElement && document.activeElement.id);

console.log("tabs");
check("init shows only the selected panel", (await panels()) === "p1");
check("roving tabindex", (await page.$$eval('#tabs [role="tab"]', (ts) => ts.map((t) => t.tabIndex).join())) === "0,-1,-1,-1");
await page.click("#t2");
check("click selects", (await selected()) === "t2" && (await panels()) === "p2");
await page.keyboard.press("ArrowRight");
check("ArrowRight skips the disabled tab", (await selected()) === "t4" && (await focused()) === "t4" && (await panels()) === "p4");
await page.keyboard.press("ArrowRight");
check("ArrowRight wraps", (await selected()) === "t1");
await page.keyboard.press("End");
check("End", (await selected()) === "t4");
await page.keyboard.press("Home");
check("Home", (await selected()) === "t1");
await page.keyboard.press("ArrowLeft");
check("ArrowLeft wraps back", (await selected()) === "t4");
await $("#tabs", (el) => el.setAttribute("dir", "rtl"));
await page.keyboard.press("ArrowLeft");
check("RTL: ArrowLeft moves forward", (await selected()) === "t1");
await $("#tabs", (el) => { el.removeAttribute("dir"); el.setAttribute("aria-orientation", "vertical"); });
await page.keyboard.press("ArrowDown");
check("vertical: ArrowDown moves forward", (await selected()) === "t2");

console.log("slider · color input · checkbox");
const fill = () => $("#slider", (el) => el.style.getPropertyValue("--my-slider-fill"));
check("fill set on load (50 of 0-200)", (await fill()) === "25%", await fill());
await $("#slider", (el) => { el.value = "150"; el.dispatchEvent(new Event("input", { bubbles: true })); });
check("fill follows input", (await fill()) === "75%", await fill());
await $('#color input[type="color"]', (el) => { el.value = "#0b6e4f"; el.dispatchEvent(new Event("input", { bubbles: true })); });
check("swatch -> text", (await $('#color input[type="text"]', (el) => el.value)) === "#0b6e4f");
await page.fill('#color input[type="text"]', "#FF8800");
check("text -> swatch", (await $('#color input[type="color"]', (el) => el.value)) === "#ff8800");
await page.fill('#color input[type="text"]', "#ff88");
check("partial hex leaves the swatch alone", (await $('#color input[type="color"]', (el) => el.value)) === "#ff8800");
check("data-indeterminate sets .indeterminate", await $("#mixed", (el) => el.indeterminate));

console.log("dialog");
const isOpen = () => $("#dlg", (el) => el.open);
await page.click("#open");
check("data-open opens modally", (await isOpen()) && (await $("#dlg", (el) => el.matches(":modal"))));
await page.click("#close");
check("data-close closes with its value", !(await isOpen()) && (await $("#dlg", (el) => el.returnValue)) === "saved");
await page.click("#open");
await page.mouse.click(640, 450);
check("click inside the dialog keeps it open", await isOpen());
await page.mouse.click(8, 8);
check("data-light-dismiss: backdrop click closes", !(await isOpen()));

console.log("menu · popover");
const box = (sel) => $(sel, (el) => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, left: r.left, right: r.right }; });
const expanded = (sel) => page.waitForFunction((s) => document.querySelector(s).getAttribute("aria-expanded") === "true", sel);
await page.click("#menubtn");
await expanded("#menubtn");
let a = await box("#menubtn"), m = await box("#menu");
check("menu opens under its trigger", (await $("#menu", (el) => el.matches(":popover-open"))) && Math.abs(m.top - (a.bottom + 6)) <= 1 && Math.abs(m.left - a.left) <= 1, JSON.stringify({ a, m }));
check("trigger gets aria-expanded", (await $("#menubtn", (el) => el.getAttribute("aria-expanded"))) === "true");
check("first item focused", (await focused()) === "mi1");
await page.keyboard.press("ArrowDown");
check("ArrowDown moves", (await focused()) === "mi2");
await page.keyboard.press("ArrowDown");
check("skips the disabled item and wraps", (await focused()) === "mi1");
await page.keyboard.press("Enter");
await page.waitForFunction(() => document.querySelector("#menubtn").getAttribute("aria-expanded") === "false", null, { timeout: 2000 }).catch(() => {});
check("Enter chooses and closes", !(await $("#menu", (el) => el.matches(":popover-open"))) && (await $("#menubtn", (el) => el.getAttribute("aria-expanded"))) === "false");
await page.click("#popbtn");
await expanded("#popbtn");
a = await box("#popbtn"); m = await box("#pop");
check("placed panel is visible again", (await $("#pop", (el) => getComputedStyle(el).visibility)) === "visible");
check("popover opens under its trigger", Math.abs(m.top - (a.bottom + 6)) <= 1 && Math.abs(m.left - a.left) <= 1, JSON.stringify({ a, m }));
await page.keyboard.press("Escape");
// near the bottom edge the panel flips above
await $("#popbtn", (el) => { el.style.position = "fixed"; el.style.bottom = "12px"; el.style.left = "40px"; });
await page.click("#popbtn");
await expanded("#popbtn");
a = await box("#popbtn"); m = await box("#pop");
check("flips above when there is no room below", Math.abs(m.bottom - (a.top - 6)) <= 1, JSON.stringify({ a, m }));
await page.keyboard.press("Escape");
await $("#popbtn", (el) => el.removeAttribute("style"));

console.log("tooltip");
await page.hover("#tipbtn");
a = await box("#tipbtn");
const tip = await page.$(".my-tooltip");
m = tip ? await box(".my-tooltip") : null;
check("hover shows it above the trigger, centred", !!m && Math.abs(m.bottom - (a.top - 6)) <= 1 && Math.abs((m.left + m.right) / 2 - (a.left + a.right) / 2) <= 1, JSON.stringify({ a, m }));
check("aria-describedby points at it", !!tip && (await $("#tipbtn", (el) => el.getAttribute("aria-describedby") === document.querySelector(".my-tooltip").id)));
await page.keyboard.press("Escape");
check("Escape hides", (await page.$(".my-tooltip")) === null && (await $("#tipbtn", (el) => !el.hasAttribute("aria-describedby"))));
await page.mouse.move(0, 0);
await page.focus("#open");
await page.keyboard.press("Tab");
await page.keyboard.press("Tab");
await page.keyboard.press("Tab");
check("keyboard focus shows it", (await focused()) === "tipbtn" && (await page.$(".my-tooltip")) !== null, await focused());
await page.keyboard.press("Tab");
check("blur hides", (await page.$(".my-tooltip")) === null);

console.log("media");
await page.click('#audio [data-media="mute"]');
check("mute toggles", (await $("#audio audio", (el) => el.muted)) && (await $('#audio [data-media="mute"]', (el) => el.getAttribute("aria-pressed") + el.getAttribute("aria-label"))) === "trueUnmute");
// one second of silence as a WAV, so play / time / scrub have something real to act on
await $("#audio audio", (el) => {
  const rate = 8000, n = rate * 2, buf = new ArrayBuffer(44 + n), v = new DataView(buf);
  const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  str(0, "RIFF"); v.setUint32(4, 36 + n, true); str(8, "WAVEfmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate, true); v.setUint16(32, 1, true); v.setUint16(34, 8, true); str(36, "data"); v.setUint32(40, n, true);
  new Uint8Array(buf, 44).fill(128);
  el.src = URL.createObjectURL(new Blob([buf], { type: "audio/wav" }));
  return new Promise((r) => el.addEventListener("loadedmetadata", r, { once: true }));
});
check("duration shown once loaded", (await $("#audio .my-media-time", (el) => el.textContent)) === "0:00 / 0:02", await $("#audio .my-media-time", (el) => el.textContent));
await page.click('#audio [data-media="play"]');
await page.waitForTimeout(300);
check("play starts and relabels to Pause", (await $("#audio audio", (el) => !el.paused)) && (await $("#audio", (el) => el.dataset.state)) === "playing" && (await $('#audio [data-media="play"]', (el) => el.getAttribute("aria-label"))) === "Pause");
await page.click('#audio [data-media="play"]');
check("second press pauses", (await $("#audio audio", (el) => el.paused)) && (await $("#audio", (el) => el.dataset.state)) === "paused");
await $("#audio .my-slider", (el) => { el.value = "1"; el.dispatchEvent(new Event("input", { bubbles: true })); });
check("scrubbing seeks", Math.abs((await $("#audio audio", (el) => el.currentTime)) - 1) < 0.05);

console.log("dismiss · toast");
await page.click("#alert [data-dismiss]");
check("data-dismiss removes the alert", (await page.$("#alert")) === null);
await page.evaluate(() => { window.t1 = MyCSS.toast("Saved", { tone: "success", duration: 400 }); window.t2 = MyCSS.toast("Failed", { tone: "danger", duration: 0 }); });
const toasts = () => page.$$eval(".my-toast-region > .my-toast", (ts) => ts.map((t) => t.getAttribute("role") + ":" + (t.dataset.tone || "") + ":" + t.querySelector("p").textContent).join());
check("toasts stack in the region with status / alert roles", (await toasts()) === "status:success:Saved,alert:danger:Failed", await toasts());
const rg = await $(".my-toast-region", (el) => { const r = el.getBoundingClientRect(); return { right: innerWidth - r.right, bottom: innerHeight - r.bottom, pos: getComputedStyle(el).position }; });
check("region is fixed to the bottom inline-end corner", rg.pos === "fixed" && rg.right > 0 && rg.right < 64 && rg.bottom > 0 && rg.bottom < 64, JSON.stringify(rg));
await page.waitForTimeout(700);
check("timed toast leaves, duration 0 stays", (await toasts()) === "alert:danger:Failed", await toasts());
await page.evaluate(() => { window.t3 = MyCSS.toast("Hover me", { duration: 300 }); });
await page.hover(".my-toast-region > .my-toast:last-child p");
await page.waitForTimeout(600);
check("hovering holds a toast", (await page.$$(".my-toast-region > .my-toast")).length === 2);
await page.mouse.move(0, 0);
await page.waitForTimeout(600);
check("and it leaves after the pointer does", (await page.$$(".my-toast-region > .my-toast")).length === 1);
await page.click(".my-toast-region [data-dismiss]");
check("dismiss button removes a toast", (await page.$$(".my-toast-region > .my-toast")).length === 0);
check("message is inserted as text, not HTML", await page.evaluate(() => { const t = MyCSS.toast("<img src=x onerror=alert(1)>", { duration: 0 }); const ok = t.querySelector("img") === null; t.remove(); return ok; }));

// ---------- 4. brand kit reaches the components (acme: accent #0B6E4F, Work Sans)
console.log("brand kit (acme)");
const probes = { button: "backgroundColor", link: "color", checkbox: "backgroundColor", radio: "backgroundColor", switch: "backgroundColor", tab: "color", "nav-link": "color", "page-button": "backgroundColor", badge: "backgroundColor", spinner: "borderTopColor" };
const kit = await page.evaluate((probes) => {
  const read = (id) => Object.fromEntries(Object.entries(probes).map(([k, prop]) => [k, getComputedStyle(document.querySelector(`#${id} [data-probe="${k}"]`))[prop]]));
  const font = (id) => getComputedStyle(document.querySelector(`#${id} [data-probe="button"]`)).fontFamily;
  return { plain: read("plain"), acme: read("acme"), fonts: [font("plain"), font("acme")] };
}, probes);
// green-dominant = the kit's hue; the default accent (rebecca purple) never is
const greenish = (c) => { const m = c.match(/[\d.]+/g).map(Number); return c.startsWith("rgb") ? m[1] > m[0] && m[1] > m[2] : /oklch|color\(/.test(c); };
for (const k of Object.keys(probes))
  check(`${k}: ${kit.plain[k]} -> ${kit.acme[k]}`, kit.plain[k] !== kit.acme[k] && greenish(kit.acme[k]) && !greenish(kit.plain[k]));
check("solid button is the brand colour exactly", kit.acme.button === "rgb(11, 110, 79)", kit.acme.button);
check("typeface switches to the kit's", /Work Sans/.test(kit.fonts[1]) && !/Work Sans/.test(kit.fonts[0]), kit.fonts.join(" | "));

check("no console or page errors during the run", errors.length === 0, errors.join(" | "));
await browser.close();
const failed = results.filter((r) => !r).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
