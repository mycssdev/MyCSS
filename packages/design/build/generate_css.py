#!/usr/bin/env python3
"""MyCSS token -> CSS pipeline (alpha).

Reads the DTCG token file (Penpot flavor) and emits:
  dist/css/mycss-tokens.css     custom properties + theme blocks (@layer mycss.tokens)
  dist/css/mycss-utilities.css  u-* utility classes (@layer mycss.utilities)
  dist/css/mycss.css            bundle (layer order declaration + both layers)

Naming conventions (settled 2026-07-23):
  - custom property prefix: --my-
  - token path -> var name: dots become dashes, underscores kept
    (bg.neutral-primary_hover -> --my-bg-neutral-primary_hover)
  - linear-scale tokens get a `space-` stem ({2} -> --my-space-2) since bare
    numeric custom property names would be unreadable
  - themes activate via data attributes: data-mode / data-accent / data-gray /
    data-density / data-typeface, one per orthogonal theme group
  - utility classes: u-<token-name>

Scale math (ms-*, linear scale) is emitted as live CSS round()/calc() over the
seed variables (--my-scale-base, --my-scale-ratio, --my-linear-base), so
density themes only override seeds + semantic spacing remaps and the whole
system recalculates in the browser.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.1.0-alpha.1"
PREFIX = "--my-"

UNIT_TYPES = {"dimension", "spacing", "sizing", "fontSizes", "borderRadius", "borderWidth"}
SKIP_TYPES = {"string", "typography"}  # icon style strings, Penpot composite styles

# v2.17.1: the purple accent is "rebecca" (was "brand"), matching Figma.
# 2026-11-15: the default accent is "base", as in Figma; rebecca is the demo
# brand colour and is opt-in with data-accent="rebecca".
# v2.18: the deprecated data-accent="brand" alias is gone.

DEFAULTS = {"gray": "slate", "accent": "base", "mode": "light",
            "density": "comfortable", "typeface": "montserrat", "depth": "soft",
            "shape": "subtle", "motion": "full"}

# Depth v0.3 (2026-09-13): geometry is a fixed octave ladder in
# foundations/fixed → shadow.*; a level is how many octaves it carries; a mode
# changes only the ink (depth/<mode> → shadow.<layer>.color aliases into the
# appearance effect.depth.* tokens, which alias the gray palette).
DEPTH_LEVELS = {"low": ["o2", "o1", "ring"],
                "mid": ["o4", "o3", "o2", "o1", "ring"],
                "high": ["o6", "o5", "o4", "o3", "o2", "o1", "ring"]}

# v2.17 (2026-11-06 decisions): projection = which way the shadow falls, read
# from the same ladder (down stays the implied default, so shadow-low|mid|high
# keep their names). start/end are logical: x is multiplied by --my-dir, which
# is -1 under RTL; inset = recessed wells (inner shadow from above + hairline).
PROJECTIONS = ("around", "up", "start", "end")
INSET_LEVELS = {"low": ["o1", "ring"], "mid": ["o2", "o1", "ring"]}

def _px(v):
    return "0" if v == 0 else f"{v}px"

def _ladder(res):
    lad = res.data["foundations/fixed"]["shadow"]
    return {k: {f: g[f]["$value"] for f in g} for k, g in lad.items()}

def _ring(L):
    r = L["ring"]
    return f"0 {_px(r['y'])} {_px(r['blur'])} {_px(r['spread'])} var({PREFIX}shadow-ring-color)"

def projection_value(L, proj, layers):
    parts = []
    for layer in layers:
        if layer == "ring":
            parts.append(_ring(L))
            continue
        g, ink = L[layer], f"var({PREFIX}shadow-{layer}-color)"
        x, y, spread = 0, g["y"], g["spread"]
        if proj == "up":
            y = g["reverse"]
        elif proj in ("start", "end"):
            x, y = (g["reverse"] if proj == "start" else g["y"]), 0
        elif proj == "around":           # offset + spread two rungs below the blur
            k = int(layer[1:])
            lo = L.get(f"o{k - 2}")
            y, spread = (lo["y"], lo["spread"]) if lo else (0, 0)
        xs = f"calc({_px(x)} * var({PREFIX}dir))" if x else "0"
        parts.append(f"{xs} {_px(y)} {_px(g['blur'])} {_px(spread)} {ink}")
    return ", ".join(parts)

def inset_value(L, layers):
    parts = []
    for layer in layers:
        if layer == "ring":
            parts.append("inset " + _ring(L))
        else:
            g = L[layer]
            parts.append(f"inset 0 {_px(g['y'])} {_px(g['blur'])} 0 var({PREFIX}shadow-{layer}-color)")
    return ", ".join(parts)

def projection_lines(res, indent, only=None):
    """Composed v2.17 shadows; only=("start","end") for the [dir] re-declare."""
    L = _ladder(res)
    out = []
    for proj in (only or PROJECTIONS):
        for lvl, layers in DEPTH_LEVELS.items():
            out.append(f"{indent}{PREFIX}shadow-{proj}-{lvl}: {projection_value(L, proj, layers)};")
    if not only:
        for lvl, layers in INSET_LEVELS.items():
            out.append(f"{indent}{PREFIX}shadow-inset-{lvl}: {inset_value(L, layers)};")
    return out

def shape_lines(res, mode, indent):
    """10. Shape (2026-11-14): radius steps per shape mode, px. Same names as
    the Figma variables: border/radius/soft -> --my-border-radius-soft,
    border/radius-outer/<x> -> --my-border-radius-outer-<x>. Default = the
    Figma collection default (Subtle); switch with data-shape."""
    out = [f"{indent}/* shape: {mode} */"]
    for path, (_t, val) in flatten(res.data[f"shape/{mode}"]).items():
        out.append(f"{indent}{PREFIX}{path.replace('.', '-')}: {_px(val)};")
    return out

def motion_lines(res, mode, indent):
    """14. Motion (2026-11-14): durations/staggers in ms, easing curves as-is.
    Default Full; Reduced via data-motion or prefers-reduced-motion."""
    out = [f"{indent}/* motion: {mode} */"]
    for path, (typ, val) in flatten(res.data[f"motion/{mode}"]).items():
        css = f"{val}ms" if typ == "number" else val
        out.append(f"{indent}{PREFIX}{path.replace('.', '-')}: {css};")
    return out

def depth_shadow_lines(res, mode, indent):
    """Per-layer ink vars for one depth mode + the composed box-shadow ladder."""
    data = res.data
    lines = [f"{indent}/* depth: {mode} */"]
    lines += emit_set(res, f"depth/{mode}", indent)          # --my-shadow-<layer>-color
    ladder = data["foundations/fixed"]["shadow"]
    px = lambda v: "0" if v == 0 else f"{v}px"
    for lvl, layers in DEPTH_LEVELS.items():
        parts = []
        for layer in layers:
            g = ladder[layer]
            y, blur, spread = (g[k]["$value"] for k in ("y", "blur", "spread"))
            parts.append(f"0 {px(y)} {px(blur)} {px(spread)} var({PREFIX}shadow-{layer}-color)")
        lines.append(f"{indent}{PREFIX}shadow-{lvl}: {', '.join(parts)};")
    lines += projection_lines(res, indent)                    # v2.17
    return lines

# Composition thresholds (CSS-stage spec, 2026-07-23) — intrinsic layout switch
# points, named per content behavior (not devices). Aliased to width tokens.
# Consumed by c-switcher's flex-basis trick and available for @container/@media.
THRESHOLDS = {
    "threshold-compact": "width-sm",        # 480px — below: content stacks
    "threshold-comfortable": "width-xl",    # 768px — balanced layouts switch here
    "threshold-spacious": "width-2xl",      # 1024px — sidebars/full layouts
    "threshold-max": "container-max-width", # 1280px — content width ceiling
}

# Container sizes (grid system, 2026-11-25) — the widths at which sized knobs
# (--my-grid-columns-md, --my-cell-span-lg, --my-col-span-xl ...) take effect,
# measured on the nearest .c-container, never the viewport. `xs` is the base
# (0, no query). These are SIZE names, not the width ladder: size md is
# width-xl. var() is not allowed in @container conditions, so the px values
# are resolved here and written to _sizes.generated.scss; the width tokens
# stay the single source.
CONTAINER_SIZES = {
    "sm": "width-sm",    # 480
    "md": "width-xl",    # 768
    "lg": "width-2xl",   # 1024
    "xl": "width-3xl",   # 1280
    "2xl": "width-4xl",  # 1440
}


def container_sizes_px(data):
    base = data["foundations/scales"]["linear-base"]["$value"]
    out = {}
    for size, tok in CONTAINER_SIZES.items():
        step = str(data["width"][tok]["$value"]).strip("{}")
        out[size] = int(float(step) * float(base))
    assert list(out.values()) == sorted(out.values()), f"container sizes must ascend: {out}"
    return out


# semantic/spacing v1.0 (per MyCSS-Spacing-Tokens.md) — pure aliases to Tier-2 spacing
SEMANTIC_SPACING = {
    "inset-none": "spacing-none", "inset-xs": "spacing-xs", "inset-sm": "spacing-md",
    "inset-md": "spacing-xl", "inset-lg": "spacing-3xl", "inset-xl": "spacing-4xl",
    "squish-block-sm": "spacing-xs", "squish-block-md": "spacing-md", "squish-block-lg": "spacing-lg",
    "squish-inline-sm": "spacing-lg", "squish-inline-md": "spacing-xl", "squish-inline-lg": "spacing-2xl",
    "stack-xs": "spacing-xs", "stack-sm": "spacing-md", "stack-md": "spacing-xl",
    "stack-lg": "spacing-3xl", "stack-xl": "spacing-4xl", "stack-2xl": "spacing-6xl",
    "inline-xs": "spacing-xxs", "inline-sm": "spacing-xs", "inline-md": "spacing-md",
    "inline-lg": "spacing-xl",
    "gutter-sm": "spacing-3xl", "gutter-md": "spacing-4xl", "gutter-lg": "spacing-6xl",
    "region-xs": "spacing-4xl", "region-sm": "spacing-6xl", "region-md": "spacing-7xl",
    "region-lg": "spacing-8xl", "region-xl": "spacing-9xl",
}

LINEAR_SET = "foundations/linear-scale"


def flatten(node, path=""):
    """Flatten a token set into {path: (type, value)}."""
    out = {}
    if isinstance(node, dict):
        if "$value" in node:
            out[path] = (node.get("$type"), node["$value"])
        else:
            for k, v in node.items():
                if not k.startswith("$"):
                    out.update(flatten(v, f"{path}.{k}" if path else k))
    return out


def var_name(setname, path):
    stem = path
    if setname == LINEAR_SET:
        stem = f"space-{path}"
    return PREFIX + stem.replace(".", "-")


class Resolver:
    def __init__(self, data):
        self.data = data
        self.ref_map = {}    # reference key -> css var name
        self.type_map = {}   # reference key -> $type
        for setname, node in data.items():
            if setname.startswith("$"):
                continue
            for path, (typ, _val) in flatten(node).items():
                self.ref_map[path] = var_name(setname, path)
                self.type_map.setdefault(path, typ)

    def ref_to_var(self, ref):
        if ref not in self.ref_map:
            raise KeyError(f"unresolved token reference: {{{ref}}}")
        return f"var({self.ref_map[ref]})"

    def ref_has_unit(self, ref):
        return self.type_map.get(ref) in UNIT_TYPES

    def value_to_css(self, typ, val):
        """Convert a DTCG value (literal, alias, or math expression) to CSS."""
        if isinstance(val, (int, float)):
            return str(val)
        val = str(val).strip()

        refs = re.findall(r"\{([^}]+)\}", val)

        # plain literal (no references)
        if not refs:
            return val

        # simple alias: "{ref}" possibly needing a unit
        m = re.fullmatch(r"\{([^}]+)\}", val)
        if m:
            ref = m.group(1)
            css = self.ref_to_var(ref)
            if typ in UNIT_TYPES and not self.ref_has_unit(ref):
                return f"calc({css} * 1px)"
            return css

        # math expression: optional round( ... ) around a * / chain
        return self.expr_to_css(typ, val)

    def expr_to_css(self, typ, val):
        rounded = False
        m = re.fullmatch(r"round\((.*)\)", val.strip())
        if m:
            rounded = True
            val = m.group(1)

        # tokenize: {ref}, numbers, * and /
        tokens = re.findall(r"\{[^}]+\}|[0-9]*\.?[0-9]+|[*/]", val)
        parsed = "".join(tokens).replace(" ", "")
        if parsed != val.replace(" ", ""):
            raise ValueError(f"cannot parse token expression: {val!r}")

        has_unit = False
        parts = []
        for t in tokens:
            if t.startswith("{"):
                ref = t[1:-1]
                parts.append(self.ref_to_var(ref))
                if self.ref_has_unit(ref):
                    has_unit = True
            elif t in "*/":
                parts.append(f" {t} ")
            else:
                parts.append(t)
        expr = "".join(parts)
        if typ in UNIT_TYPES and not has_unit:
            expr += " * 1px"
        if rounded:
            return f"round({expr}, 1px)"
        return f"calc({expr})"


def emit_set(res, setname, indent="  "):
    lines = []
    for path, (typ, val) in flatten(res.data[setname]).items():
        if typ in SKIP_TYPES:
            continue
        try:
            css = res.value_to_css(typ, val)
        except (KeyError, ValueError) as e:
            print(f"  ! skipped {setname}:{path} — {e}", file=sys.stderr)
            continue
        lines.append(f"{indent}{var_name(setname, path)}: {css};")
    return lines


COMPOSITION_PREFIXES = {"stack", "inline", "gutter", "inset", "region"}


def check_composition_aliases(data):
    """v2.16: the stack/inline/gutter/inset/region aliases and `threshold` now
    live in canonical (density/* sets, same value in every density) so Figma
    and CSS build from one source. The tables above remain the CSS-side spec
    (squish-* is CSS-only); this asserts the two can never drift."""
    for mode in ("compact", "comfortable", "spacious"):
        canon = {}
        for path, (_t, val) in flatten(data[f"density/{mode}"]).items():
            if path.split("-")[0] in COMPOSITION_PREFIXES:
                canon[path] = str(val).strip("{}")
        for name, ref in SEMANTIC_SPACING.items():
            if name.split("-")[0] in COMPOSITION_PREFIXES:
                assert canon.get(name) == ref, (
                    f"semantic spacing drift in density/{mode}: {name} is {canon.get(name)!r} "
                    f"in canonical but {ref!r} in SEMANTIC_SPACING")
        extra = set(canon) - set(SEMANTIC_SPACING)
        assert not extra, f"canonical density/{mode} has aliases unknown to SEMANTIC_SPACING: {sorted(extra)}"
        thr = str(flatten(data[f"density/{mode}"])["threshold"][1]).strip("{}")
        assert thr == THRESHOLDS[f"threshold-{mode}"], (
            f"threshold drift in density/{mode}: canonical {thr!r} vs THRESHOLDS {THRESHOLDS[f'threshold-{mode}']!r}")


def emit_semantic_spacing(indent="  "):
    return [f"{indent}{PREFIX}{name}: var({PREFIX}{ref});"
            for name, ref in SEMANTIC_SPACING.items()]


def theme_sets(data, group, name):
    for t in data["$themes"]:
        if t["group"] == group and t["name"] == name:
            return [k for k, v in t["selectedTokenSets"].items() if v == "enabled"]
    raise KeyError(f"theme not found: {group}/{name}")


def emit_appearance_lightdark(res, indent="  "):
    """Merge appearance/light + appearance/dark into light-dark() pairs.

    The mode axis is carried by the inherited `color-scheme` property instead of
    variable blocks: light-dark() evaluates at the *consuming* element, so
    data-mode works on any subtree with no re-declaration.
    """
    light = flatten(res.data["appearance/light"])
    dark = flatten(res.data["appearance/dark"])
    lines = []
    for path, (typ, lval) in light.items():
        dtyp, dval = dark[path]
        lcss = res.value_to_css(typ, lval)
        dcss = res.value_to_css(dtyp, dval)
        name = PREFIX + path.replace(".", "-")
        if lcss == dcss:
            lines.append(f"{indent}{name}: {lcss};")
        else:
            lines.append(f"{indent}{name}: light-dark({lcss}, {dcss});")
    return lines


def build_tokens_css(data):
    check_composition_aliases(data)
    res = Resolver(data)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = [f"/*! MyCSS tokens v{VERSION} — generated {stamp} from tokens.all-in-one.json.",
           " *  Do not edit by hand; run packages/design/build/generate_css.py.",
           " *  Requires: CSS round(), light-dark() — Baseline 2024. */",
           "@layer mycss.tokens {"]

    # ---------- :root — foundations, primitives, always-on semantics, defaults
    out.append("  :root {")
    out.append("    color-scheme: light;")
    out.append("    /* foundations */")
    for s in ["foundations/fixed", "foundations/scales", "foundations/linear-scale",
              "foundations/typography"]:
        out += emit_set(res, s, "    ")
    out.append("    /* primitives */")
    for s in sorted(k for k in data if k.startswith("primitives/")):
        out += emit_set(res, s, "    ")
    out.append("    /* status semantics (always enabled) */")
    for s in ["semantic/status-error", "semantic/status-warning",
              "semantic/status-success", "semantic/status-info"]:
        out += emit_set(res, s, "    ")
    out.append("    /* component / layout */")
    for s in ["spacing", "width", "container", "paragraph", "icon"]:
        out += emit_set(res, s, "    ")
    out.append("    /* composition thresholds (intrinsic layout switch points) */")
    for name, ref in THRESHOLDS.items():
        out.append(f"    {PREFIX}{name}: var({PREFIX}{ref});")
    # v2.16: one mode-selected threshold (the Figma variable); [data-density]
    # blocks re-declare it from canonical
    out.append(f"    {PREFIX}threshold: var({PREFIX}threshold-{DEFAULTS['density']});")
    out.append("    /* default theme: slate gray, base accent, comfortable, montserrat, soft depth */")
    for s in [f"semantic/gray-{DEFAULTS['gray']}", f"semantic/accent-{DEFAULTS['accent']}",
              f"semantic/typeface-{DEFAULTS['typeface']}"]:
        out += emit_set(res, s, "    ")
    out.append(f"    {PREFIX}dir: 1;  /* v2.17: -1 under RTL; flips start/end shadows */")
    out += depth_shadow_lines(res, DEFAULTS["depth"], "    ")
    out += shape_lines(res, DEFAULTS["shape"], "    ")
    out += motion_lines(res, DEFAULTS["motion"], "    ")
    out.append("  }")

    # ---------- orthogonal theme blocks (after :root so equal specificity wins)
    # Mode is just color-scheme: the appearance tier below uses light-dark().
    out.append('  [data-mode="light"] { color-scheme: light; }')
    out.append('  [data-mode="dark"] { color-scheme: dark; }')
    groups = [("Gray flavor", "gray"), ("Accent color", "accent"),
              ("Density", "density"), ("Typeface", "typeface")]
    for group, attr in groups:
        for t in data["$themes"]:
            if t["group"] != group:
                continue
            key = t["name"].lower()
            sel = f'[data-{attr}="{key}"]'
            out.append(f'  {sel} {{')
            for s in theme_sets(data, group, t["name"]):
                out += emit_set(res, s, "    ")
            out.append("  }")
    # depth blocks — composed shadows only (components stay token-side)
    for t in data["$themes"]:
        if t["group"] != "Depth":
            continue
        key = t["name"].lower()
        out.append(f'  [data-depth="{key}"] {{')
        out += depth_shadow_lines(res, key, "    ")
        out.append("  }")
    # shape + motion blocks (2026-11-14) — plain values, no alias tiers needed
    for group, attr, fn in (("Shape", "shape", shape_lines), ("Motion", "motion", motion_lines)):
        for t in data["$themes"]:
            if t["group"] != group:
                continue
            key = t["name"].lower()
            out.append(f'  [data-{attr}="{key}"] {{')
            out += fn(res, key, "    ")
            out.append("  }")
    out.append('  @media (prefers-reduced-motion: reduce) {')
    out.append('    :root:not([data-motion="full"]) {')
    out += motion_lines(res, "reduced", "      ")
    out.append("    }")
    out.append("  }")
    # v2.17 logical projections: start/end are composed where they're declared,
    # so re-declare them where the direction changes (RTL, and an LTR island)
    out.append("  /* direction — start/end shadows follow the inline direction */")
    out.append(f"  :dir(rtl) {{ {PREFIX}dir: -1; }}")
    out.append(f'  [dir="ltr"] {{ {PREFIX}dir: 1; }}')
    out.append('  :dir(rtl), [dir="ltr"] {')
    out += projection_lines(res, "    ", only=("start", "end"))
    out.append("  }")

    # ---------- alias tiers, re-declared at every theme boundary they depend on.
    # var() substitution inside a custom property happens at the DECLARING
    # element, so tiers that read themed variables must be re-declared wherever
    # those variables change — this is what makes subtree theming work.
    # [data-brand] (brand kits, dist/css/brandkits/) can change any themed
    # variable, so every tier is re-declared there too.
    out.append("  /* modular scale — recomputes where density changes seeds */")
    out.append("  :root, [data-density], [data-brand] {")
    out += emit_set(res, "foundations/modular-scale", "    ")
    out.append("  }")

    out.append("  /* semantic spacing v1.0 — recomputes where density remaps spacing-* */")
    out.append("  :root, [data-density], [data-brand] {")
    out += emit_semantic_spacing("    ")
    out.append("  }")

    out.append("  /* typography roles — recompute where density or typeface change */")
    out.append("  :root, [data-density], [data-typeface], [data-brand] {")
    out += emit_set(res, "typography/roles", "    ")
    out.append("  }")

    out.append("  /* appearance — recompute where gray or accent change; mode via light-dark() */")
    out.append("  :root, [data-gray], [data-accent], [data-brand] {")
    out += emit_appearance_lightdark(res, "    ")
    out.append("  }")

    out += emit_p3_primitives(res, "  ")

    out.append("}")
    return "\n".join(out) + "\n", res


P3_FILE = Path(__file__).resolve().parent.parent / "tokens" / "primitives-p3" / "tokens.primitives-p3.json"


def emit_p3_primitives(res, indent="  "):
    """v2.16.1: Radix Colors v3 Display-P3 overrides for the sRGB primitives.

    Same delivery as @radix-ui/colors' *-p3 CSS: only browsers that support
    color(display-p3) AND sit on a P3-capable display get them. Every P3 var
    must already exist as an sRGB primitive (asserted), so this block can only
    refine values, never add names."""
    if not P3_FILE.exists():
        return []
    p3 = json.loads(P3_FILE.read_text(encoding="utf-8"))
    srgb = set(res.ref_map.values())
    lines = [f"{indent}/* Radix Colors v3 Display-P3 (CSS-only; design tools stay sRGB) */",
             # COLOR() upper-case on purpose: CSS function names are
             # case-insensitive, but dart-sass (1.80) rejects lower-case
             # color() inside @supports when @use-ing this file as plain CSS.
             f"{indent}@supports (color: COLOR(display-p3 1 1 1)) {{",
             f"{indent}  @media (color-gamut: p3) {{",
             f"{indent}    :root {{"]
    for setname in sorted(k for k in p3 if k.startswith("primitives/")):
        for path, (_typ, val) in flatten(p3[setname]).items():
            name = var_name(setname, path)
            if name not in srgb:
                raise KeyError(f"P3 token {name} has no sRGB primitive")
            lines.append(f"{indent}      {name}: {val};")
    lines += [f"{indent}    }}", f"{indent}  }}", f"{indent}}}"]
    return lines


ROLE_NAMES = ["display-2xl", "display-xl", "display-lg", "h1", "h2", "h3", "h4", "h5", "h6",
              "body-lg", "body", "body-sm", "caption", "overline", "code",
              "label-2xl", "label-xl", "label-lg", "label", "label-sm"]


def build_utilities_css(data):
    res = Resolver(data)
    out = [f"/*! MyCSS utilities v{VERSION} — u-* classes, token-symmetric names. */",
           "@layer mycss.utilities {"]

    def rule(selector, decls):
        out.append(f"  {selector} {{")
        out.extend(f"    {p}: {v};" for p, v in decls)
        out.append("  }")

    # typography roles
    for r in ROLE_NAMES:
        rule(f".u-{r}", [
            ("font-family", f"var({PREFIX}{r}-family)"),
            ("font-size", f"var({PREFIX}{r}-size)"),
            ("font-weight", f"var({PREFIX}{r}-weight)"),
            ("line-height", f"var({PREFIX}{r}-line-height)"),
            ("letter-spacing", f"var({PREFIX}{r}-tracking)"),
        ])

    # appearance colors -> bg / text / border utilities
    appearance = flatten(data["appearance/light"])
    for path in appearance:
        name = path.replace(".", "-")
        if path.startswith("bg."):
            rule(f".u-{name}", [("background-color", f"var({PREFIX}{name})")])
        elif path.startswith("text."):
            rule(f".u-{name}", [("color", f"var({PREFIX}{name})")])
        elif path.startswith("border."):
            rule(f".u-{name}", [("border-color", f"var({PREFIX}{name})")])
        elif path.startswith("decorative."):
            # decorative colour utilities — fixed-hue roles (26 hues x 5 roles)
            # + contrast-safe pairs per the decorative usage guidance
            leaf = path.split(".", 1)[1]          # e.g. tomato-bg / tomato-on-solid
            cssvar = f"var({PREFIX}decorative-{leaf})"
            if leaf.endswith("-on-solid"):
                hue = leaf[:-9]
                rule(f".u-text-decorative-{hue}-on-solid", [("color", cssvar)])
            elif leaf.endswith("-text"):
                hue = leaf[:-5]
                rule(f".u-text-decorative-{hue}", [("color", cssvar)])
            elif leaf.endswith("-border"):
                hue = leaf[:-7]
                rule(f".u-border-decorative-{hue}", [("border-color", cssvar)])
            elif leaf.endswith("-solid"):
                hue = leaf[:-6]
                rule(f".u-bg-decorative-{hue}-solid", [("background-color", cssvar)])
                rule(f".u-decorative-{hue}-solid", [  # pair: solid + on-solid
                    ("background-color", cssvar),
                    ("color", f"var({PREFIX}decorative-{hue}-on-solid)")])
            elif leaf.endswith("-bg"):
                hue = leaf[:-3]
                rule(f".u-bg-decorative-{hue}", [("background-color", cssvar)])
                rule(f".u-decorative-{hue}", [  # pair: bg + text
                    ("background-color", cssvar),
                    ("color", f"var({PREFIX}decorative-{hue}-text)")])

    # shadow / elevation — consume the composed depth shadows; follow data-depth
    rule(".u-shadow-none", [("box-shadow", "none")])
    for lvl in ("low", "mid", "high"):
        rule(f".u-shadow-{lvl}", [("box-shadow", f"var({PREFIX}shadow-{lvl})")])
    for proj in PROJECTIONS:                                   # v2.17
        for lvl in DEPTH_LEVELS:
            rule(f".u-shadow-{proj}-{lvl}", [("box-shadow", f"var({PREFIX}shadow-{proj}-{lvl})")])
    for lvl in INSET_LEVELS:
        rule(f".u-shadow-inset-{lvl}", [("box-shadow", f"var({PREFIX}shadow-inset-{lvl})")])

    # radius
    for step in flatten(data["foundations/fixed"]):
        if step.startswith("border-radius."):
            n = step.split(".")[1]
            rule(f".u-radius-{n}", [("border-radius", f"var({PREFIX}border-radius-{n})")])

    # semantic spacing
    sizes = lambda stem: sorted({k[len(stem) + 1:] for k in SEMANTIC_SPACING if k.startswith(stem + "-")
                                 and not k.startswith(stem + "-block") and not k.startswith(stem + "-inline")},
                                key=lambda s: list(SEMANTIC_SPACING).index(f"{stem}-{s}"))
    for s in sizes("inset"):
        rule(f".u-inset-{s}", [("padding", f"var({PREFIX}inset-{s})")])
    for s in ["sm", "md", "lg"]:
        rule(f".u-squish-{s}", [("padding-block", f"var({PREFIX}squish-block-{s})"),
                                ("padding-inline", f"var({PREFIX}squish-inline-{s})")])
    for s in sizes("stack"):
        rule(f".u-stack-{s}", [("row-gap", f"var({PREFIX}stack-{s})")])
    # The two utilities that set a column gap also publish it as --my-column-gap
    # (registered non-inheriting in composition.scss). c-grid and c-columns
    # calculate with the gap, so they must know when a utility changed it.
    for s in sizes("inline"):
        rule(f".u-inline-{s}", [(f"{PREFIX}column-gap", f"var({PREFIX}inline-{s})"),
                                ("column-gap", f"var({PREFIX}inline-{s})")])
    for s in sizes("gutter"):
        rule(f".u-gutter-{s}", [(f"{PREFIX}column-gap", f"var({PREFIX}gutter-{s})"),
                                ("gap", f"var({PREFIX}gutter-{s})")])
    for s in sizes("region"):
        rule(f".u-region-{s}", [("padding-block", f"var({PREFIX}region-{s})")])

    # width constraints + paragraph measure
    for path in flatten(data["width"]):
        rule(f".u-{path}", [("max-inline-size", f"var({PREFIX}{path})")])
    rule(".u-paragraph", [("max-inline-size", f"var({PREFIX}paragraph-max-width)")])

    out.append("}")
    return "\n".join(out) + "\n"


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent / "tokens" / "all-in-one" / "tokens.all-in-one.json")
    dist = Path(__file__).resolve().parent.parent / "dist" / "css"
    dist.mkdir(parents=True, exist_ok=True)

    data = json.loads(src.read_text())
    tokens_css, res = build_tokens_css(data)
    utilities_css = build_utilities_css(data)

    (dist / "mycss-tokens.css").write_text(tokens_css)
    (dist / "mycss-utilities.css").write_text(utilities_css)

    # Token-name list for the SCSS layer: my.token() validates names at
    # compile time against this generated module.
    stems = sorted(set(re.findall(r"(?m)^\s*" + PREFIX + r"([\w-]+):", tokens_css)))
    scss_dir = Path(__file__).resolve().parent.parent / "src" / "scss"
    scss_dir.mkdir(parents=True, exist_ok=True)
    names = ("// GENERATED by generate_css.py — do not edit. Legal my.token() names.\n"
             "$all: (\n" + "".join(f'  "{s}",\n' for s in stems) + ");\n")
    (scss_dir / "_token-names.generated.scss").write_text(names)

    sizes_px = container_sizes_px(data)
    sizes_scss = ("// GENERATED by generate_css.py — do not edit. Container sizes for the\n"
                  "// sized composition knobs, resolved from the width tokens. `xs` is the\n"
                  "// base size (0) and needs no query.\n"
                  "$sizes: (\n" + "".join(
                      f'  "{n}": {v}px,  // {CONTAINER_SIZES[n]}\n' for n, v in sizes_px.items()) + ");\n")
    (scss_dir / "_sizes.generated.scss").write_text(sizes_scss)
    print(f"wrote {scss_dir}/_sizes.generated.scss ({sizes_px})")

    print(f"wrote {dist}/mycss-tokens.css ({len(tokens_css)//1024} KB)")
    print(f"wrote {dist}/mycss-utilities.css ({len(utilities_css)//1024} KB)")
    print(f"wrote {scss_dir}/_token-names.generated.scss ({len(stems)} token names)")
    print("bundle: run `npm run build:css` (sass) to produce dist/css/mycss.css")


if __name__ == "__main__":
    main()
