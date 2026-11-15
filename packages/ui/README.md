# MyCSS UI

The BLOCKS layer — CSS for the components in the My.CSS Figma library (CUBE "B").

- Source: `src/scss/blocks.scss` (index) + one partial per component in `src/scss/blocks/`.
- Output: bundled into `packages/design/dist/css/mycss.css` (layer `mycss.blocks`)
  and standalone as `packages/design/dist/css/mycss-blocks.css`.
- Build: `npm run build:css` · watch: `npm run dev`.

## Conventions

| Figma | CSS |
|---|---|
| Component `Button` | class `.my-button` |
| Variant axes (Tone, Variant, Size) | `data-tone`, `data-variant`, `data-size` (lower-case values) |
| State axis (Hover, Focus, Pressed, Disabled) | real `:hover` / `:focus-visible` / `:active` / `:disabled` + `data-state` mirror for specimens |
| Bound variables | `my.token(name)` → `var(--my-name)`, validated at compile time |
| Loading boolean | `aria-busy="true"` |

Private per-component knobs are `--_name` custom properties. No size variants
unless Figma has one (Button's Size axis); density modes scale everything else.
Cascade order: `mycss.tokens, mycss.composition, mycss.blocks, mycss.utilities`.

## Status

Specimens: `packages/design/dist/button-spec.html`, `packages/design/dist/actions-spec.html`, `packages/design/dist/inputs-forms-spec.html`, `packages/design/dist/navigation-spec.html`, `packages/design/dist/feedback-spec.html`, `packages/design/dist/overlays-spec.html`, `packages/design/dist/data-display-spec.html`, `packages/design/dist/media-content-spec.html`. Shared tone × variant × state recipe: `src/scss/blocks/_action-tones.scss` (Button, Icon Button, Split Button).


| Component | Figma page | CSS |
|---|---|---|
| Button | Actions | ✅ 2026-11-14 — all 6 tones × 4 variants × 5 states, Size XS–XL, loading. Specimen: `packages/design/dist/button-spec.html` |
| Icon Button | Actions | ✅ 2026-11-14 — 3 tones × 4 variants × 5 states; disabled keeps a border on every variant (as Figma) |
| Toggle Button | Actions | ✅ 2026-11-14 — `aria-pressed`; Off keeps a transparent border (Figma Off is 2px shorter) |
| Segmented Control + Segment | Actions | ✅ 2026-11-14 — buttons (`aria-pressed`) or radio labels (`:has(input:checked)`) |
| Split Button | Actions | ✅ 2026-11-14 — two buttons in one shape; Open = toggle `aria-expanded="true"`; 38px tall to line up with Button (Figma enabled = 36) |
| Link | Actions | ✅ 2026-11-14 — inherits surrounding font; `aria-disabled` for disabled |
| Tag | Actions | ✅ 2026-11-14 — Neutral/Brand, optional dismiss `<button>` inside |
| Button Group | Actions | ✅ 2026-11-14 — wrapping row, gap spacing-sm |
| Field, Field Label, Field Meta, Field Group | Inputs & Forms | ✅ 2026-11-14 |
| Input, Textarea, Select | Inputs & Forms | ✅ 2026-11-14 — shared recipe in `_control.scss`; Input also works as a wrapper with icons; Select paints a caret (native select has no icon slot) |
| Checkbox, Radio, Switch | Inputs & Forms | ✅ 2026-11-14 — native inputs inside a `.my-choice` label; error via `aria-invalid` |
| Slider | Inputs & Forms | ✅ 2026-11-14 — fill in Chrome/Safari follows `--my-slider-fill`, kept in step by `mycss.js`; Firefox is native |
| Color Input | Inputs & Forms | ✅ 2026-11-14 — swatch + hex text in one control; `mycss.js` keeps the two in sync |
| File Input | Inputs & Forms | ✅ 2026-11-14 — native file button as the chip |
| Menu Item, Menu panel | Inputs & Forms | ✅ 2026-11-14 — styling only; open/close and positioning come with Overlays |
| Nav Link, Navbar, Skip Link | Navigation | ✅ 2026-11-15 — current page via `aria-current`; sticky via `data-position="sticky"` |
| Sidebar Item, Sidebar (expanded, rail), Nav Drawer panel | Navigation | ✅ 2026-11-15 — drawer open/close and positioning come with Overlays |
| Disclosure, Accordion | Navigation | ✅ 2026-11-15 — native `<details>`; shared `name` keeps one open |
| Tabs | Navigation | ✅ 2026-11-15 — horizontal and vertical; arrow keys, Home/End and panel switching from `mycss.js` |
| Breadcrumb | Navigation | ✅ 2026-11-15 — separators drawn by CSS |
| Pagination | Navigation | ✅ 2026-11-15 — numbered and simple; prev/next are Icon Buttons |
| Stepper | Navigation | ✅ 2026-11-15 — horizontal and vertical; connector stretches (Figma: fixed 48px) |
| Table of Contents | Navigation | ✅ 2026-11-15 — current rail sits on the list's rule |
| Badge | Feedback | ✅ 2026-11-15 — status (soft, outline), count, dot; static |
| Alert, Toast | Feedback | ✅ 2026-11-15 — tones share `_status.scss`; `MyCSS.toast()` stacks and times toasts in `.my-toast-region` |
| Progress Bar, Meter | Feedback | ✅ 2026-11-15 — native `<progress>` / `<meter>`; meter band comes from low/high/optimum |
| Spinner, Skeleton, Empty State | Feedback | ✅ 2026-11-15 — skeleton is static, as in Figma |
| Dialog, Alert Dialog | Overlays | ✅ 2026-11-15 — native `<dialog>` + `showModal()` (browser handles focus, Esc, scrim); also works on a `<div>` |
| Drawer | Overlays | ✅ 2026-11-15 — left, right, bottom; left/right swap in RTL |
| Popover, Tooltip, Menu extras | Overlays | ✅ 2026-11-15 — native `popover` attribute; `mycss.js` places the panel by its trigger and shows `data-tooltip` tooltips |
| Table | Data Display | ✅ 2026-11-15 — wrapper is the surface and scroll container; sort via `aria-sort`, selection via `aria-selected`, zebra via `data-striped` |
| List, Description List | Data Display | ✅ 2026-11-15 |
| Card, Stat | Data Display | ✅ 2026-11-15 — interactive card: the title link covers the card |
| Code, Kbd | Data Display | ✅ 2026-11-15 |
| Avatar, Avatar Group | Data Display | ✅ 2026-11-15 — sizes sm / md / lg |
| Timeline, Tree, Divider | Data Display | ✅ 2026-11-15 — tree branches are native `<details>` |
| Media Frame / Image, Figure | Media & Content | ✅ 2026-11-15 — ratio via `data-ratio`; loading and error states |
| Media Controls, Video, Audio | Media & Content | ✅ 2026-11-15 — `data-media="play|mute|fullscreen"` buttons, time and scrubber wired by `mycss.js` |
| Embed | Media & Content | ✅ 2026-11-15 — provider chip and consent facade |
| Blockquote, inline text (`.my-prose`), Media Object | Media & Content | ✅ 2026-11-15 |

All seven BLOCKS pages have CSS.

## Script

`src/js/mycss.js` (copied to `packages/design/dist/js/mycss.js` by `npm run build:js`) is the small amount of script the components need. No dependencies, one file, about 16 KB unminified. Load it with `<script src="js/mycss.js" defer></script>`. Everything works by class or attribute through event delegation, so there is nothing to initialise; call `MyCSS.init(root)` only after inserting sliders, indeterminate checkboxes or tab lists later.

| Behaviour | Markup |
|---|---|
| Tabs: arrow keys (RTL and vertical aware), Home/End, roving tabindex, panels | `.my-tabs[role="tablist"]` with `[role="tab"][aria-controls="panel-id"]` |
| Slider fill | `input.my-slider` |
| Color Input sync | `.my-color-input` with a color and a text input |
| Indeterminate checkbox | `input.my-checkbox[data-indeterminate]` |
| Open / close a dialog or drawer | `data-open="#id"` on a trigger, `data-close` (optionally `="value"`) inside, `data-light-dismiss` on the `<dialog>` for backdrop clicks |
| Dismiss | `data-dismiss` on a button inside `.my-alert`, `.my-toast` or `.my-tag` |
| Popover / Menu placement | `popovertarget="id"` on the trigger; panel opens under it, flips above near the bottom edge, sets `aria-expanded`. Menus also get arrow keys, Home/End, Enter/Space |
| Tooltip | `data-tooltip="text"` on the trigger; hover and keyboard focus, Esc hides |
| Media | `<video>`/`<audio>` inside `.my-video`/`.my-audio`, buttons with `data-media="play"`, `"mute"`, `"fullscreen"`, `.my-media-time`, a `.my-slider` scrubber |
| Toast | `MyCSS.toast("Saved", { tone: "success", duration: 5000, dismissible: true })`; `duration: 0` stays until dismissed; `danger` announces as an alert, the rest as status |

Not covered by the script: focus trapping (native `<dialog>` does it), sortable tables, tree keyboard navigation beyond native `<details>`, Split Button menus beyond `popovertarget`, and CSS anchor positioning (placement is computed once on open and is not updated on scroll or resize).

## Tests

`npm test` runs `tools/tests/verify.mjs` (tokens, theming, layout) and `tools/tests/blocks.mjs`: every `.my-*` class used in a specimen has CSS and every class in the CSS is shown in a specimen, each specimen page loads without errors, each script behaviour above, and the example brand kit reaching the accent-driven components.
