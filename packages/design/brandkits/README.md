# MyCSS brand kits

A brand kit is for a brand whose colours or type fall outside the built-in
choices (27 accent hues, 6 grays, 5 typefaces). One JSON file per brand here;
`npm run build:brandkits` writes `dist/css/brandkits/mycss.brandkit.<name>.css`.

```html
<link rel="stylesheet" href="css/mycss.css">
<link rel="stylesheet" href="css/brandkits/mycss.brandkit.acme.css">  <!-- after mycss.css -->
```

## Switching a kit on

| Attribute | Effect |
|---|---|
| `data-brand="acme"` | The whole kit: accent, neutral, families, weights, scale, and its shape / depth / density choices |
| `data-accent="acme"` | Only the kit's accent colour |
| `data-gray="acme"` | Only the kit's neutral |
| `data-typeface="acme"` | Only the kit's font families and weights |

An explicit `data-accent`, `data-gray`, `data-typeface`, `data-shape`,
`data-depth` or `data-density` on the same element beats the `data-brand`
bundle. All of them work on any subtree, not just `<html>`.

## Kit format (`<name>.json`; every section is optional)

```jsonc
{
  "name": "acme",                      // = file name; lower-case, not a built-in name
  "label": "Acme Corp",
  "accent": {
    "hex": "#0B6E4F",                  // becomes step 9, exactly
    "pin": { "light": { "11": "#075c41" }, "dark": { "9": "#18a577" } },  // fix any of steps 1-12
    "contrast": "#ffffff"              // text on the brand colour; or { "light": "#fff", "dark": "#101820" };
                                       // default is chosen automatically per mode
  },                                   // or "accent": "blue" (a built-in, data-brand only)
  "neutral": { "hex": "#8A8378", "pin": { "light": {}, "dark": {} } },    // or "neutral": "sand"
  "typography": {
    "import": ["https://fonts.googleapis.com/css2?family=Work+Sans:wght@400..800"],
    "families": { "primary": "'Work Sans', system-ui, sans-serif", "secondary": "…", "mono": "…" },
    "weights": {
      "steps": { "bold": 800 },        // re-value regular | medium | semibold | bold
      "roles": { "display": 800, "heading": 700, "body": 400, "label": "semibold" }
    },                                 // role groups: display, heading, body, label, overline, code
    "scale": { "base": 17, "ratio": 1.2, "compact": { "base": 15 } }
  },
  "recipe": { "shape": "sharp", "depth": "flat", "density": "comfortable" }   // built-in modes
}
```

## How the colours are made

- **Accent:** a Python port of the method behind Radix's custom-palette tool.
  It blends the two closest built-in Radix scales, takes the brand colour's
  hue and chroma, keeps the scale's lightness curve, and puts the exact brand
  hex at step 9 (light and dark). Step 10 (hover) is derived from step 9.
- **Step 9 exception:** if the hex would vanish into the page (within 0.10
  OKLab of white, or 0.20 of the dark background `#111111`), step 9 is a
  generated colour for that mode and the build says so. Pin step 9 to choose.
- **Neutral:** the closest built-in gray, re-tinted with the hex's hue and chroma.
- **Alpha steps:** the most transparent colour that composites back to exactly
  the solid step on white (light) or `#111111` (dark).
- **Text step:** same rule as the built-in hues (v2.16.2): light-mode
  `text-brand` uses step 11 if it reaches WCAG AA 4.5:1 on neutral 1–3 (all
  six built-in grays and the kit's own) and on the accent's steps 3–4;
  otherwise step 12. The build prints the worst-case ratios and warns below 4.5.
- sRGB only: kit colours have no Display-P3 variant.

Accuracy: generated from a built-in hue's own step 9, the ramp lands within
ΔE(OK) 0.01–0.05 of the real Radix light ramp (mean 0.003–0.02; checked on blue, orange, jade, crimson, amber). Dark ramps
match as closely except step 10, which the method darkens where Radix's
hand-tuned scales lighten (ΔE ≈ 0.08). Pin steps where the brand guide says so.

## Scale and density

`scale.base` / `scale.ratio` are the kit's Comfortable scale. Compact and
Spacious keep MyCSS's proportions to it (base × 14/16 and × 18/16, rounded to
0.5px; ratio stretched the same way) unless the kit gives `scale.compact` /
`scale.spacious`. The scale applies with `data-brand` only, and follows nested
`data-density` inside the brand.

## Not covered yet

Figma (modes or extended collections), logos and other brand assets, custom
shape / depth values (a kit picks from the built-in modes).
