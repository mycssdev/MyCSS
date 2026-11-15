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

Specimens: `packages/design/dist/button-spec.html`, `packages/design/dist/actions-spec.html`, `packages/design/dist/inputs-forms-spec.html`. Shared tone × variant × state recipe: `src/scss/blocks/_action-tones.scss` (Button, Icon Button, Split Button).


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
| Slider | Inputs & Forms | ✅ 2026-11-14 — fill in Chrome/Safari follows `--my-slider-fill` (set from JS); Firefox is native |
| Color Input | Inputs & Forms | ✅ 2026-11-14 — swatch + hex text in one control; syncing the two is the page's job |
| File Input | Inputs & Forms | ✅ 2026-11-14 — native file button as the chip |
| Menu Item, Menu panel | Inputs & Forms | ✅ 2026-11-14 — styling only; open/close and positioning come with Overlays |
| Everything else | — | not started |
