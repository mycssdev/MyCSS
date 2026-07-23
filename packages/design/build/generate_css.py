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

DEFAULTS = {"gray": "slate", "accent": "brand", "mode": "light",
            "density": "comfortable", "typeface": "inter"}

# Composition thresholds (CSS-stage spec, 2026-07-23) — intrinsic layout switch
# points, named per content behavior (not devices). Aliased to width tokens.
# Consumed by c-switcher's flex-basis trick and available for @container/@media.
THRESHOLDS = {
    "threshold-compact": "width-sm",        # 480px — below: content stacks
    "threshold-comfortable": "width-xl",    # 768px — balanced layouts switch here
    "threshold-spacious": "width-2xl",      # 1024px — sidebars/full layouts
    "threshold-max": "container-max-width", # 1280px — content width ceiling
}

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
    out.append("    /* default theme: slate gray, brand accent, comfortable, inter */")
    for s in [f"semantic/gray-{DEFAULTS['gray']}", f"semantic/accent-{DEFAULTS['accent']}",
              f"semantic/typeface-{DEFAULTS['typeface']}"]:
        out += emit_set(res, s, "    ")
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
            out.append(f'  [data-{attr}="{key}"] {{')
            for s in theme_sets(data, group, t["name"]):
                out += emit_set(res, s, "    ")
            out.append("  }")

    # ---------- alias tiers, re-declared at every theme boundary they depend on.
    # var() substitution inside a custom property happens at the DECLARING
    # element, so tiers that read themed variables must be re-declared wherever
    # those variables change — this is what makes subtree theming work.
    out.append("  /* modular scale — recomputes where density changes seeds */")
    out.append("  :root, [data-density] {")
    out += emit_set(res, "foundations/modular-scale", "    ")
    out.append("  }")

    out.append("  /* semantic spacing v1.0 — recomputes where density remaps spacing-* */")
    out.append("  :root, [data-density] {")
    out += emit_semantic_spacing("    ")
    out.append("  }")

    out.append("  /* typography roles — recompute where density or typeface change */")
    out.append("  :root, [data-density], [data-typeface] {")
    out += emit_set(res, "typography/roles", "    ")
    out.append("  }")

    out.append("  /* appearance — recompute where gray or accent change; mode via light-dark() */")
    out.append("  :root, [data-gray], [data-accent] {")
    out += emit_appearance_lightdark(res, "    ")
    out.append("  }")

    out.append("}")
    return "\n".join(out) + "\n", res


ROLE_NAMES = ["display-2xl", "display-xl", "display-lg", "h1", "h2", "h3", "h4", "h5", "h6",
              "body-lg", "body", "body-sm", "caption", "overline", "code",
              "label-lg", "label", "label-sm"]


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
    for s in sizes("inline"):
        rule(f".u-inline-{s}", [("column-gap", f"var({PREFIX}inline-{s})")])
    for s in sizes("gutter"):
        rule(f".u-gutter-{s}", [("gap", f"var({PREFIX}gutter-{s})")])
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

    print(f"wrote {dist}/mycss-tokens.css ({len(tokens_css)//1024} KB)")
    print(f"wrote {dist}/mycss-utilities.css ({len(utilities_css)//1024} KB)")
    print(f"wrote {scss_dir}/_token-names.generated.scss ({len(stems)} token names)")
    print("bundle: run `npm run build:css` (sass) to produce dist/css/mycss.css")


if __name__ == "__main__":
    main()
