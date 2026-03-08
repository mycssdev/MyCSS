# MyCSS GitHub Repository Setup

## Folder Structure

```
mycss/
├── README.md
├── LICENSE
├── .gitignore
│
├── packages/
│   ├── design/                         # MyCSS Design — Multi-brand design system
│   │   ├── README.md
│   │   ├── tokens/
│   │   │   ├── all-in-one/
│   │   │   │   └── tokens.all-in-one.json       # Complete token file (AIO)
│   │   │   ├── foundations/
│   │   │   │   └── tokens.foundations.json      # Fixed values, scales, modular/linear scale, typography foundations
│   │   │   ├── primitives/
│   │   │   │   └── tokens.primitives.json       # All Radix color palettes + base, brand, alpha colors
│   │   │   ├── semantic/
│   │   │   │   ├── tokens.semantic-colors.json  # Accent, gray flavor, status color aliases
│   │   │   │   └── tokens.semantic-typography.json  # Typeface aliases (Inter, Geist, Roboto, System)
│   │   │   ├── appearance/
│   │   │   │   └── tokens.appearance.json       # Light & dark mode appearance tokens
│   │   │   ├── density/
│   │   │   │   └── tokens.density.json          # Compact, comfortable, spacious density scales
│   │   │   ├── spacing/
│   │   │   │   └── tokens.spacing.json          # Spacing, width, container, paragraph tokens
│   │   │   ├── icons/
│   │   │   │   └── tokens.icons.json            # Icon size tokens
│   │   │   └── typography/
│   │   │       └── tokens.typography.json       # Typography roles & styles
│   │   └── penpot/                     # Penpot-specific exports (future)
│   │
│   ├── ui/                             # MyCSS UI — HTML/CSS/JS components
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── css/
│   │   │   └── js/
│   │   └── dist/
│   │
│   ├── composition/                    # MyCSS Composition — Layout collection
│   │   ├── README.md
│   │   └── src/
│   │       ├── layouts/
│   │       └── css/
│   │
│   ├── pages/                          # MyCSS Pages — Full page designs
│   │   ├── README.md
│   │   └── src/
│   │       ├── landing/
│   │       ├── marketing/
│   │       └── web/
│   │
│   └── ai/                             # MyCSS AI — Vibe coding/designing tool
│       ├── README.md
│       └── src/
│
├── docs/                               # Documentation
│   ├── index.md
│   ├── getting-started.md
│   ├── design-system/
│   │   ├── tokens/
│   │   │   ├── overview.md
│   │   │   ├── foundations.md
│   │   │   ├── primitives.md
│   │   │   ├── semantic.md
│   │   │   ├── appearance.md
│   │   │   ├── density.md
│   │   │   ├── spacing.md
│   │   │   └── typography.md
│   │   └── theming.md
│   ├── ui/
│   ├── composition/
│   └── pages/
│
└── tools/                              # Shared build/gen tooling
    ├── scripts/
    │   ├── token-split.py              # Script to split AIO tokens into files
    │   └── color-convert.py            # OKLCH color conversion utilities
    └── config/
        └── token-sets.json             # Token set configuration reference
```

---

## Claude Code Setup Instructions

Paste the following prompt into **Claude Code** at the root of your cloned `mycss` repo:

---

```
Create the following folder and file structure for the MyCSS monorepo. 
For each folder, create a .gitkeep file to preserve empty directories. 
For each README.md listed, create a minimal placeholder with the package name as an H1 heading.

Run these commands:

# Root files
touch README.md LICENSE .gitignore

# packages/design — token directories
mkdir -p packages/design/tokens/all-in-one
mkdir -p packages/design/tokens/foundations
mkdir -p packages/design/tokens/primitives
mkdir -p packages/design/tokens/semantic
mkdir -p packages/design/tokens/appearance
mkdir -p packages/design/tokens/density
mkdir -p packages/design/tokens/spacing
mkdir -p packages/design/tokens/icons
mkdir -p packages/design/tokens/typography
mkdir -p packages/design/penpot
touch packages/design/README.md

# packages/ui
mkdir -p packages/ui/src/components
mkdir -p packages/ui/src/css
mkdir -p packages/ui/src/js
mkdir -p packages/ui/dist
touch packages/ui/README.md

# packages/composition
mkdir -p packages/composition/src/layouts
mkdir -p packages/composition/src/css
touch packages/composition/README.md

# packages/pages
mkdir -p packages/pages/src/landing
mkdir -p packages/pages/src/marketing
mkdir -p packages/pages/src/web
touch packages/pages/README.md

# packages/ai
mkdir -p packages/ai/src
touch packages/ai/README.md

# docs
mkdir -p docs/design-system/tokens
mkdir -p docs/ui
mkdir -p docs/composition
mkdir -p docs/pages
touch docs/index.md
touch docs/getting-started.md
touch docs/design-system/tokens/overview.md
touch docs/design-system/tokens/foundations.md
touch docs/design-system/tokens/primitives.md
touch docs/design-system/tokens/semantic.md
touch docs/design-system/tokens/appearance.md
touch docs/design-system/tokens/density.md
touch docs/design-system/tokens/spacing.md
touch docs/design-system/tokens/typography.md
touch docs/design-system/theming.md

# tools
mkdir -p tools/scripts
mkdir -p tools/config
touch tools/scripts/token-split.py
touch tools/scripts/color-convert.py
touch tools/config/token-sets.json

# Add .gitkeep to all empty dist/src leaves
find packages -type d -empty -exec touch {}/.gitkeep \;
find docs -type d -empty -exec touch {}/.gitkeep \;
find tools -type d -empty -exec touch {}/.gitkeep \;

echo "✅ MyCSS repo structure created."
```

After running the above, copy the token files into their respective folders:

```
# Token files go into packages/design/tokens/
cp tokens.all-in-one.json          packages/design/tokens/all-in-one/
cp tokens.foundations.json         packages/design/tokens/foundations/
cp tokens.primitives.json          packages/design/tokens/primitives/
cp tokens.semantic-colors.json     packages/design/tokens/semantic/
cp tokens.semantic-typography.json packages/design/tokens/semantic/
cp tokens.appearance.json          packages/design/tokens/appearance/
cp tokens.density.json             packages/design/tokens/density/
cp tokens.spacing.json             packages/design/tokens/spacing/
cp tokens.icons.json               packages/design/tokens/icons/
cp tokens.typography.json          packages/design/tokens/typography/
```

---

## Token Files Reference

| File | Contents | Size |
|------|----------|------|
| `tokens.all-in-one.json` | Every token set — use for full imports | ~343KB |
| `tokens.foundations.json` | Fixed constants, scale params, modular/linear scales | ~19KB |
| `tokens.primitives.json` | All 35 Radix color palettes + base, brand, alpha | ~134KB |
| `tokens.semantic-colors.json` | 37 accent/gray/status semantic alias sets | ~162KB |
| `tokens.semantic-typography.json` | 4 typeface alias sets (Inter, Geist, Roboto, System) | ~9KB |
| `tokens.appearance.json` | Light & dark mode appearance tokens | ~24KB |
| `tokens.density.json` | Compact, comfortable, spacious density scales | ~13KB |
| `tokens.spacing.json` | Spacing, width, container, paragraph tokens | ~10KB |
| `tokens.icons.json` | Icon size tokens | ~9KB |
| `tokens.typography.json` | Typography roles & styles | ~23KB |

---

## Package Overview

| Package | Description |
|---------|-------------|
| `packages/design` | Multi-brand design system tokens for Penpot & Figma |
| `packages/ui` | UI elements in HTML, CSS, JavaScript |
| `packages/composition` | HTML layouts collection (intrinsic web design) |
| `packages/pages` | Full designs — landing pages, marketing sites |
| `packages/ai` | Vibe coding/designing tool |
