# MyCSS Composition

The CUBE "C" layer: `.c-*` layout classes. Source is
`src/scss/composition.scss`; `src/css/composition.css` is its compiled
plain-CSS copy. Live spec and stress test: `packages/design/dist/grid-spec.html`.

Primitives: `c-stack`, `c-cluster`, `c-center`, `c-sidebar`, `c-switcher`,
`c-cover`, and the grid system below.

## Grid system

Nothing reads the viewport. Most of it has no queries at all; the *sized*
knobs are container queries against the nearest `.c-container`.

| Class | What it is | Queries |
|---|---|---|
| `c-grid` | Smart grid: as many columns as fit | none |
| `c-grid[data-layout="fixed"]` | Explicit tracks + cells | container |
| `c-columns` | Flexbox columns with spans | none (sized spans: container) |
| `c-page` | Page grid with breakout lines | none |
| `c-container` | Marks the element the sizes are measured on | — |

### Knobs

A knob is a custom property set on one instance, e.g.
`style="--my-grid-columns: 3"`.

| Knob | On | Does |
|---|---|---|
| `--my-grid-min` | `c-grid` | Smallest a column may get (default `width-3xs`, 256px) |
| `--my-grid-space` | `c-grid` | Gap (default `gutter-md`) |
| `--my-grid-columns` | `c-grid` | Smart: most columns per row. Fixed: track count (12) |
| `--my-grid-placement` | `c-grid` | `auto-fit` (default) or `auto-fill` |
| `--my-cell-span`, `--my-cell-start`, `--my-cell-rows` | a fixed-grid cell | Width, position, height in tracks |
| `--my-grid-rows`, `--my-grid-row-space` | `c-grid[data-subgrid="rows"]` | Shared rows per item (3) and their gap |
| `--my-col-span` | a `c-columns` child | Share of `--my-columns-count` (12) |
| `--my-columns-min`, `--my-columns-space`, `--my-columns-count` | `c-columns` | Narrowest column, gap, share base |
| `--my-page-content`, `-popout`, `-feature`, `-gutter` | `c-page` | Track widths |

Exceptions (data attributes): `data-span="full"` (smart-grid item),
`data-subgrid` (cell), `data-subgrid="rows"` (grid), `data-col="shrink"`
(column), `data-breakout="popout|feature|full"` (page child).

### Sizes

`--my-grid-columns`, `--my-cell-span`, `--my-cell-start` and `--my-col-span`
take a size suffix. A sized knob applies from that size **up**, until a
larger one overrides it.

| Size | Container width from | Width token |
|---|---|---|
| `xs` | 0 (no container needed) | — |
| `sm` | 480px | `width-sm` |
| `md` | 768px | `width-xl` |
| `lg` | 1024px | `width-2xl` |
| `xl` | 1280px | `width-3xl` |
| `2xl` | 1440px | `width-4xl` |

These are size names, not the width ladder: size `md` is 768px, while
`--my-width-md` is 560px. The values are generated from the width tokens into
`packages/design/src/scss/_sizes.generated.scss` by `generate_css.py`
(`CONTAINER_SIZES`), because `var()` cannot be used in a query condition.

```html
<div class="c-container">
  <div class="c-grid" data-layout="fixed" style="--my-grid-columns-sm: 12">
    <article style="--my-cell-span: 12; --my-cell-span-sm: 6; --my-cell-span-lg: 4">…</article>
  </div>
</div>
```

The fixed grid's defaults are one column below `md`, then
`--my-grid-columns` (12). With no `.c-container` it stays one column.

### Rules

- **Change the gap only with the knob or a gap utility** (`u-gutter-*`,
  `u-inline-*`, `u-stack-*`). The grid calculates with the gap; the utilities
  publish theirs as `--my-column-gap`, a raw `gap:` does not. When both a
  utility and a knob are set, the utility wins.
- **`.c-container` needs its width from outside** (a block, a grid cell, a
  column). Inside anything that shrink-wraps (`c-cluster`, `inline-block`,
  `fit-content`) it collapses to zero. Put it on a wrapper, not on the grid.
  It is not the centring wrapper; that is `c-center`.
- **Numeric spans belong to the fixed grid.** On the smart grid only
  `data-span="full"` is safe.
- **Many tracks and wide gaps need room.** 12 tracks have 11 gaps.
- In the SCSS, the sized-knob block must stay last in the layer.

### Tested

`npm test` runs `tools/tests/grid.mjs`: 2,000 checks (25 stages × 16 widths ×
5 modes). The same self-test runs in any browser from the button on
`grid-spec.html`. As of 2026-11-25 this build passes in Chromium 153,
WebKitGTK 2.52, Firefox 160 and Safari 26.6 (0 unexpected in each). Re-run
the button in Firefox and Safari after any change to the grid; `npm test`
only covers Chromium.
