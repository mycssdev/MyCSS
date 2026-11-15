/*! MyCSS UI behaviours v0.1.0-alpha — the small amount of script the BLOCKS
    components need. No dependencies, no build step, safe to load twice.

    <script src="js/mycss.js" defer></script>

    Everything is progressive: the markup works (or degrades sensibly)
    without it. Behaviours attach by class / attribute through event
    delegation, so content added later needs no re-init, except the three
    that set initial state: call MyCSS.init(root) after inserting sliders,
    indeterminate checkboxes or tab lists.

    Tabs            .my-tabs[role=tablist] > [role=tab][aria-controls]   arrows, Home/End, panels
    Slider fill     .my-slider                                          keeps --my-slider-fill in step
    Color Input     .my-color-input                                     swatch <-> hex text
    Checkbox        .my-checkbox[data-indeterminate]                    sets .indeterminate
    Dialog/Drawer   [data-open="#id"] · [data-close] · dialog[data-light-dismiss]
    Dismiss         [data-dismiss] inside .my-alert / .my-toast / .my-tag
    Popover/Menu    [popovertarget] + .my-popover/.my-menu[popover]     placed by the trigger
    Tooltip         [data-tooltip="text"]                               hover + focus, Esc hides
    Media           .my-video / .my-audio with a <video>/<audio> and [data-media="play|mute|fullscreen"]
    Toast           MyCSS.toast("Saved", { tone: "success", duration: 5000 })
*/
(function () {
  "use strict";
  if (window.MyCSS && window.MyCSS.version) return;
  const doc = document;
  const rtl = (el) => getComputedStyle(el).direction === "rtl";

  // ---------- Slider fill (Chrome / Safari have no filled-track part)
  function sliderFill(el) {
    const min = parseFloat(el.min) || 0;
    const max = el.max === "" ? 100 : parseFloat(el.max);
    const pct = max > min ? ((parseFloat(el.value) - min) / (max - min)) * 100 : 0;
    el.style.setProperty("--my-slider-fill", Math.min(100, Math.max(0, pct)) + "%");
  }
  doc.addEventListener("input", (e) => {
    const t = e.target;
    if (!(t instanceof Element)) return;
    if (t.matches("input.my-slider")) sliderFill(t);
    // ---------- Color Input: swatch <-> hex text
    const box = t.closest(".my-color-input");
    if (box) {
      const color = box.querySelector('input[type="color"]');
      const text = box.querySelector('input[type="text"], output');
      if (t === color && text) {
        if ("value" in text) text.value = color.value; else text.textContent = color.value;
      } else if (t === text && color && /^#[0-9a-f]{6}$/i.test(text.value.trim())) {
        color.value = text.value.trim().toLowerCase();
      }
    }
  });

  // ---------- Tabs
  function selectTab(tab, focus) {
    const list = tab.closest('[role="tablist"]');
    if (!list || tab.disabled || tab.getAttribute("aria-disabled") === "true") return;
    list.querySelectorAll('[role="tab"]').forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      const panel = t.getAttribute("aria-controls") && doc.getElementById(t.getAttribute("aria-controls"));
      if (panel) panel.hidden = !on;
    });
    if (focus) tab.focus();
  }
  doc.addEventListener("click", (e) => {
    const tab = e.target instanceof Element && e.target.closest('.my-tabs [role="tab"]');
    if (tab) selectTab(tab, false);
  });
  doc.addEventListener("keydown", (e) => {
    const tab = e.target instanceof Element && e.target.closest('.my-tabs [role="tab"]');
    if (!tab) return;
    const list = tab.closest('[role="tablist"]');
    const tabs = [...list.querySelectorAll('[role="tab"]')].filter((t) => !t.disabled && t.getAttribute("aria-disabled") !== "true");
    const vertical = list.getAttribute("aria-orientation") === "vertical";
    const i = tabs.indexOf(tab);
    const fwd = vertical ? "ArrowDown" : rtl(list) ? "ArrowLeft" : "ArrowRight";
    const back = vertical ? "ArrowUp" : rtl(list) ? "ArrowRight" : "ArrowLeft";
    let next = null;
    if (e.key === fwd) next = tabs[(i + 1) % tabs.length];
    else if (e.key === back) next = tabs[(i - 1 + tabs.length) % tabs.length];
    else if (e.key === "Home") next = tabs[0];
    else if (e.key === "End") next = tabs[tabs.length - 1];
    if (next) { e.preventDefault(); selectTab(next, true); }
  });

  // ---------- Dialog / Drawer triggers, dismiss buttons
  doc.addEventListener("click", (e) => {
    if (!(e.target instanceof Element)) return;
    const opener = e.target.closest("[data-open]");
    if (opener) {
      const dlg = doc.querySelector(opener.getAttribute("data-open"));
      if (dlg && typeof dlg.showModal === "function" && !dlg.open) dlg.showModal();
      return;
    }
    const closer = e.target.closest("[data-close]");
    if (closer) {
      const dlg = closer.closest("dialog");
      if (dlg) dlg.close(closer.getAttribute("data-close") || "");
      return;
    }
    const dismiss = e.target.closest("[data-dismiss]");
    if (dismiss) {
      const box = dismiss.closest(".my-toast, .my-alert, .my-tag");
      if (box) removeToast(box);
      return;
    }
    // light dismiss: a click on the backdrop lands on the <dialog> itself
    if (e.target.matches("dialog[data-light-dismiss]")) {
      const r = e.target.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) e.target.close();
    }
  });

  // ---------- Placement for popovers, menus and tooltips
  function place(el, anchor, side) {
    const gap = 6, pad = 8;
    el.style.position = "fixed";
    el.style.margin = "0";
    el.style.inset = "auto";
    const a = anchor.getBoundingClientRect();
    const w = el.offsetWidth, h = el.offsetHeight;
    const vw = doc.documentElement.clientWidth, vh = doc.documentElement.clientHeight;
    let top = side === "top" ? a.top - h - gap : a.bottom + gap;
    if (side !== "top" && top + h > vh - pad && a.top - h - gap >= pad) top = a.top - h - gap;   // flip up
    if (side === "top" && top < pad) top = a.bottom + gap;                                        // flip down
    let left = side === "top" ? a.left + (a.width - w) / 2 : rtl(anchor) ? a.right - w : a.left;
    left = Math.min(Math.max(pad, left), Math.max(pad, vw - w - pad));
    el.style.top = Math.round(top) + "px";
    el.style.left = Math.round(left) + "px";
  }
  function invokerOf(pop) {
    return pop.id ? doc.querySelector('[popovertarget="' + CSS.escape(pop.id) + '"]') : null;
  }
  // the toggle event arrives a task after the panel is shown, so keep it
  // invisible until it has been placed: no flash in the default position
  doc.addEventListener("beforetoggle", (e) => {
    const pop = e.target;
    if (pop instanceof Element && pop.matches(".my-popover[popover], .my-menu[popover]") && e.newState === "open" && invokerOf(pop)) pop.style.visibility = "hidden";
  }, true);
  doc.addEventListener("toggle", (e) => {
    const pop = e.target;
    if (!(pop instanceof Element) || !pop.matches(".my-popover[popover], .my-menu[popover]")) return;
    const inv = invokerOf(pop);
    if (inv) inv.setAttribute("aria-expanded", e.newState === "open" ? "true" : "false");
    if (e.newState === "open" && inv) { place(pop, inv, "bottom"); pop.style.visibility = ""; }
    if (e.newState === "open" && pop.matches(".my-menu")) {
      // menu items are often plain elements: make them focusable, start on the first
      const items = [...pop.querySelectorAll(".my-menu-item")];
      items.forEach((i) => { if (!i.hasAttribute("tabindex") && !i.matches("button, a[href]")) i.tabIndex = -1; });
      const first = items.find((i) => !i.matches(':disabled, [aria-disabled="true"]'));
      if (first) first.focus();
    }
  }, true);
  // menus: arrow keys move between items; choosing an item closes the menu
  doc.addEventListener("keydown", (e) => {
    const menu = e.target instanceof Element && e.target.closest(".my-menu");
    if (!menu || !["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) return;
    const items = [...menu.querySelectorAll(".my-menu-item")].filter((i) => !i.matches(':disabled, [aria-disabled="true"]'));
    if (!items.length) return;
    const i = items.indexOf(doc.activeElement);
    const next = e.key === "Home" ? items[0] : e.key === "End" ? items[items.length - 1]
      : e.key === "ArrowDown" ? items[(i + 1) % items.length] : items[(i - 1 + items.length) % items.length];
    e.preventDefault();
    next.focus();
  });
  doc.addEventListener("keydown", (e) => {
    const item = e.target instanceof Element && e.target.closest(".my-menu .my-menu-item");
    if (item && !item.matches("button, a[href]") && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); item.click(); }
  });
  doc.addEventListener("click", (e) => {
    const item = e.target instanceof Element && e.target.closest(".my-menu[popover] .my-menu-item");
    if (item && !item.matches('[role="menuitemcheckbox"], [role="menuitemradio"], :disabled, [aria-disabled="true"]')) {
      item.closest(".my-menu").hidePopover();
    }
  });

  // ---------- Tooltip
  let tip = null, tipFor = null, tipSeq = 0;
  function showTip(el) {
    const text = el.getAttribute("data-tooltip");
    if (!text || tipFor === el) return;
    hideTip();
    tip = doc.createElement("span");
    tip.className = "my-tooltip";
    tip.setAttribute("role", "tooltip");
    tip.id = "my-tooltip-" + ++tipSeq;
    tip.textContent = text;
    tip.style.zIndex = "2147483000";
    // inside an open dialog the tooltip must live in the same top-layer subtree
    (el.closest("dialog[open], [popover]:popover-open") || doc.body).appendChild(tip);
    place(tip, el, "top");
    el.setAttribute("aria-describedby", tip.id);
    tipFor = el;
  }
  function hideTip() {
    if (tip) tip.remove();
    if (tipFor) tipFor.removeAttribute("aria-describedby");
    tip = tipFor = null;
  }
  const tipTarget = (e) => (e.target instanceof Element ? e.target.closest("[data-tooltip]") : null);
  doc.addEventListener("pointerover", (e) => { const t = tipTarget(e); if (t) showTip(t); });
  doc.addEventListener("pointerout", (e) => { const t = tipTarget(e); if (t && !t.contains(e.relatedTarget)) hideTip(); });
  doc.addEventListener("focusin", (e) => { const t = tipTarget(e); if (t && t.matches(":focus-visible")) showTip(t); });
  doc.addEventListener("focusout", (e) => { if (tipTarget(e)) hideTip(); });
  doc.addEventListener("keydown", (e) => { if (e.key === "Escape") hideTip(); });
  window.addEventListener("scroll", hideTip, true);

  // ---------- Media controls (custom controls under a <video> / <audio>)
  const fmt = (s) => { s = Math.max(0, Math.floor(s || 0)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
  function mediaOf(el) {
    const host = el.closest(".my-video, .my-audio");
    return host ? { host, media: host.querySelector("video, audio") } : null;
  }
  function syncMedia(media) {
    const host = media.closest(".my-video, .my-audio");
    if (!host) return;
    host.dataset.state = media.paused ? "paused" : "playing";
    host.querySelectorAll('[data-media="play"]').forEach((b) => {
      b.setAttribute("aria-pressed", String(!media.paused));
      b.setAttribute("aria-label", media.paused ? "Play" : "Pause");
    });
    host.querySelectorAll('[data-media="mute"]').forEach((b) => {
      b.setAttribute("aria-pressed", String(media.muted));
      b.setAttribute("aria-label", media.muted ? "Unmute" : "Mute");
    });
    const time = host.querySelector(".my-media-time");
    if (time) time.textContent = fmt(media.currentTime) + " / " + fmt(media.duration);
    const scrub = host.querySelector(".my-media-controls .my-slider");
    if (scrub && doc.activeElement !== scrub && media.duration) {
      scrub.max = String(media.duration);
      scrub.value = String(media.currentTime);
      sliderFill(scrub);
    }
  }
  doc.addEventListener("click", (e) => {
    const btn = e.target instanceof Element && e.target.closest("[data-media]");
    const m = btn && mediaOf(btn);
    if (!m || !m.media) return;
    const action = btn.getAttribute("data-media");
    if (action === "play") m.media.paused ? m.media.play().catch(() => {}) : m.media.pause();
    else if (action === "mute") m.media.muted = !m.media.muted;
    else if (action === "fullscreen") doc.fullscreenElement ? doc.exitFullscreen() : (m.host.requestFullscreen && m.host.requestFullscreen());
    syncMedia(m.media);
  });
  doc.addEventListener("input", (e) => {
    const s = e.target instanceof Element && e.target.closest(".my-media-controls .my-slider");
    const m = s && mediaOf(s);
    if (m && m.media && isFinite(m.media.duration)) m.media.currentTime = parseFloat(s.value);
  });
  ["play", "pause", "timeupdate", "loadedmetadata", "volumechange", "ended"].forEach((type) =>
    doc.addEventListener(type, (e) => { if (e.target instanceof HTMLMediaElement) syncMedia(e.target); }, true));

  // ---------- Toast
  function region() {
    let r = doc.querySelector(".my-toast-region");
    if (!r) {
      r = doc.createElement("div");
      r.className = "my-toast-region";
      r.setAttribute("role", "region");
      r.setAttribute("aria-label", "Notifications");
      doc.body.appendChild(r);
    }
    return r;
  }
  function removeToast(el) {
    clearTimeout(el._myTimer);
    el.remove();
  }
  const ICONS = {
    neutral: '<circle cx="10" cy="10" r="7"/><path d="M10 9v4.5M10 6.5h.01"/>',
    info: '<circle cx="10" cy="10" r="7"/><path d="M10 9v4.5M10 6.5h.01"/>',
    success: '<circle cx="10" cy="10" r="7"/><path d="M7 10.5l2 2 4-4.5"/>',
    warning: '<path d="M10 3l7.5 13h-15z"/><path d="M10 8v3.5M10 14h.01"/>',
    danger: '<circle cx="10" cy="10" r="7"/><path d="M10 6.5v4M10 13.5h.01"/>',
  };
  function toast(message, opts) {
    opts = opts || {};
    const tone = ICONS[opts.tone] ? opts.tone : "neutral";
    const el = doc.createElement("div");
    el.className = "my-toast";
    if (tone !== "neutral") el.dataset.tone = tone;
    // errors interrupt (alert); everything else waits its turn (status)
    el.setAttribute("role", tone === "danger" ? "alert" : "status");
    el.innerHTML = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICONS[tone] + "</svg><p></p>";
    el.querySelector("p").textContent = String(message);
    if (opts.dismissible !== false) {
      const b = doc.createElement("button");
      b.className = "my-icon-button";
      b.dataset.tone = "neutral";
      b.dataset.variant = "ghost";
      b.setAttribute("data-dismiss", "");
      b.setAttribute("aria-label", "Dismiss");
      b.innerHTML = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8"/></svg>';
      el.appendChild(b);
    }
    region().appendChild(el);
    const ms = opts.duration === undefined ? 5000 : opts.duration;
    if (ms > 0) {
      const arm = () => { el._myTimer = setTimeout(() => removeToast(el), ms); };
      arm();
      // reading or focusing a toast keeps it on screen
      el.addEventListener("pointerenter", () => clearTimeout(el._myTimer));
      el.addEventListener("pointerleave", arm);
      el.addEventListener("focusin", () => clearTimeout(el._myTimer));
      el.addEventListener("focusout", arm);
    }
    return el;
  }

  // ---------- initial state
  function init(root) {
    root = root || doc;
    root.querySelectorAll("input.my-slider").forEach(sliderFill);
    root.querySelectorAll("input.my-checkbox[data-indeterminate]").forEach((c) => { c.indeterminate = true; });
    root.querySelectorAll('.my-tabs[role="tablist"]').forEach((list) => {
      const tabs = [...list.querySelectorAll('[role="tab"]')];
      const current = tabs.find((t) => t.getAttribute("aria-selected") === "true") || tabs[0];
      if (current) selectTab(current, false);
    });
    root.querySelectorAll(".my-video video, .my-audio audio").forEach(syncMedia);
  }
  window.MyCSS = { version: "0.1.0-alpha.1", init, toast };
  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", () => init());
  else init();
})();
