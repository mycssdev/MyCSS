#!/usr/bin/env python3
"""MyCSS brand kits -> dist/css/brandkits/mycss.brandkit.<name>.css

A brand kit is for a brand whose colours or type fall outside the built-in
choices (27 accent hues, 6 grays, 5 typefaces). One JSON file per brand in
packages/design/brandkits/; one CSS file out, loaded after mycss.css:

    <link rel="stylesheet" href="css/mycss.css">
    <link rel="stylesheet" href="css/brandkits/mycss.brandkit.acme.css">

Two ways to switch it on (both always generated):
    data-brand="acme"                       the whole kit in one attribute
    data-accent="acme" data-gray="acme" data-typeface="acme"
                                            its parts, mixed with built-ins
An explicit data-accent / data-gray / data-typeface / data-shape / data-depth
/ data-density on the same element always beats the data-brand bundle.

Usage: generate_brandkit.py [kit.json ...]      (no args = every kit)
See packages/design/brandkits/README.md for the kit format.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brandkit_color as K          # noqa: E402
import generate_css as G            # noqa: E402

ROOT = HERE.parent
CANONICAL = ROOT / "tokens" / "all-in-one" / "tokens.all-in-one.json"
KITS = ROOT / "brandkits"
OUT = ROOT / "dist" / "css" / "brandkits"
P = G.PREFIX
LIGHT_BG, DARK_BG = "#ffffff", "#111111"
GRAYS = ["gray", "mauve", "slate", "sage", "olive", "sand"]
NOT_RADIX = {"rebecca", "base", "black-alpha", "white-alpha"}
ROLE_GROUPS = {
    "display": ["display-2xl", "display-xl", "display-lg"],
    "heading": ["h1", "h2", "h3", "h4", "h5", "h6"],
    "body": ["body-lg", "body", "body-sm", "caption"],
    "label": ["label-2xl", "label-xl", "label-lg", "label", "label-sm"],
    "overline": ["overline"],
    "code": ["code"],
}
WEIGHT_STEPS = ("regular", "medium", "semibold", "bold")


class KitError(Exception):
    pass


def load_scales(data, dark):
    out = {}
    for key in data:
        if key.startswith("primitives/"):
            hue = key.split("/", 1)[1]
            if hue not in NOT_RADIX:
                grp = data[key][hue + ("-dark" if dark else "")]
                out[hue] = [K.hex_to_lch(grp[str(i)]["$value"]) for i in range(1, 13)]
    return out


def theme_names(data, group):
    return [t["name"].lower() for t in data["$themes"] if t["group"] == group]


def check_hex(value, where):
    if not isinstance(value, str) or not re.fullmatch(r"#?[0-9a-fA-F]{6}", value.strip()):
        raise KitError(f"{where}: expected a 6-digit hex colour, got {value!r}")
    return "#" + value.strip().lstrip("#").lower()


def apply_pins(steps, pins, where):
    pinned = []
    for step, value in (pins or {}).items():
        if str(step) not in {str(i) for i in range(1, 13)}:
            raise KitError(f"{where}: pin step must be 1-12, got {step!r}")
        steps[int(step) - 1] = check_hex(value, f"{where} pin {step}")
        pinned.append(int(step))
    return sorted(pinned)


def ramp_lines(prefix, steps, bg, indent):
    lines = [f"{indent}{P}{prefix}-{i}: {h};" for i, h in enumerate(steps, 1)]
    lines += [f"{indent}{P}{prefix}-alpha-a{i}: {K.alpha_of(h, bg)};" for i, h in enumerate(steps, 1)]
    return lines


def build_kit(kit, data, res):
    name = kit.get("name", "")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        raise KitError("name: lower-case letters, digits and hyphens, starting with a letter")
    taken = ({k.split("/", 1)[1] for k in data if k.startswith("primitives/")} | {"brand", "accent", "neutral"}
             | set(theme_names(data, "Typeface")))
    if name in taken:
        raise KitError(f"name {name!r} collides with a built-in MyCSS name")
    notes, report = [], []
    root, blocks = [], []          # :root primitives; (selector, lines) blocks
    brand = f'[data-brand="{name}"]'
    sel = lambda axis: f'[data-{axis}="{name}"], {brand}:not([data-{axis}])'
    bundle = lambda axis: f'{brand}:not([data-{axis}])'
    builtin = lambda axis, group, value: value in theme_names(data, group) or (_ for _ in ()).throw(
        KitError(f"{axis}: {value!r} is not a built-in ({', '.join(theme_names(data, group))})"))

    # ---------------- neutral (first: accent text is checked against it)
    neutral = kit.get("neutral")
    kit_neutral_light = None
    if isinstance(neutral, dict):
        hx = check_hex(neutral.get("hex"), "neutral.hex")
        light, mix_l = K.gray_scale(hx, {g: load_scales(data, False)[g] for g in GRAYS}, LIGHT_BG)
        dark, mix_d = K.gray_scale(hx, {g: load_scales(data, True)[g] for g in GRAYS}, DARK_BG)
        pl = apply_pins(light, (neutral.get("pin") or {}).get("light"), "neutral light")
        pd = apply_pins(dark, (neutral.get("pin") or {}).get("dark"), "neutral dark")
        kit_neutral_light = light
        root += [f"    /* neutral: tinted from {hx} */"]
        root += ramp_lines(f"{name}-neutral", light, LIGHT_BG, "    ")
        root += ramp_lines(f"{name}-neutral-dark", dark, DARK_BG, "    ")
        lines = []
        for src, dst in (("", ""), ("-alpha", "-alpha"), ("-dark", "-dark"), ("-dark-alpha", "-dark-alpha")):
            pre = "a" if "alpha" in src else ""
            lines += [f"    {P}neutral{dst}-{pre}{i}: var({P}{name}-neutral{src}-{pre}{i});" for i in range(1, 13)]
        blocks.append((sel("gray"), lines))
        report.append(f"neutral {hx}: light from {mix_l['mix'][0]}, dark from {mix_d['mix'][0]}"
                      + (f"; pinned light {pl}" if pl else "") + (f"; pinned dark {pd}" if pd else ""))
    elif isinstance(neutral, str):
        builtin("neutral", "Gray flavor", neutral)
        blocks.append((bundle("gray"), G.emit_set(res, f"semantic/gray-{neutral}", "    ")))
        report.append(f"neutral: built-in {neutral} (data-brand only)")

    # ---------------- accent
    accent = kit.get("accent")
    if isinstance(accent, dict):
        hx = check_hex(accent.get("hex"), "accent.hex")
        light, con_l, n_l = K.accent_scale(hx, load_scales(data, False), GRAYS, LIGHT_BG)
        dark, _con_d, n_d = K.accent_scale(hx, load_scales(data, True), GRAYS, DARK_BG)
        pl = apply_pins(light, (accent.get("pin") or {}).get("light"), "accent light")
        pd = apply_pins(dark, (accent.get("pin") or {}).get("dark"), "accent dark")
        # text on the brand colour: one hex, or {"light": hex, "dark": hex}
        # when the two modes' step 9 need different text
        given = accent.get("contrast")
        if isinstance(given, dict):
            contrast = check_hex(given.get("light"), "accent.contrast.light") if given.get("light") else K.text_on(light[8])
            contrast_d = check_hex(given.get("dark"), "accent.contrast.dark") if given.get("dark") else K.text_on(dark[8])
        else:
            contrast = check_hex(given, "accent.contrast") if given else K.text_on(light[8])
            contrast_d = contrast if given else K.text_on(dark[8])
        # v2.16.2 rule: step 11 for text if it reaches 4.5:1 on neutral 1-3
        # (every built-in gray + the kit's own) and on this accent's 3-4.
        grounds = [light[2], light[3]]
        for g in GRAYS:
            grounds += [data[f"primitives/{g}"][g][str(i)]["$value"] for i in (1, 2, 3)]
        if kit_neutral_light:
            grounds += kit_neutral_light[:3]
        worst11 = min(K.wcag_contrast(light[10], g) for g in grounds)
        worst12 = min(K.wcag_contrast(light[11], g) for g in grounds)
        text_step = 11 if worst11 >= 4.5 else 12
        root += [f"    /* accent: {hx} */"]
        root += ramp_lines(name, light, LIGHT_BG, "    ")
        root += ramp_lines(f"{name}-dark", dark, DARK_BG, "    ")
        lines = []
        for src in ("", "-alpha", "-dark", "-dark-alpha"):
            pre = "a" if "alpha" in src else ""
            lines += [f"    {P}accent{src}-{pre}{i}: var({P}{name}{src}-{pre}{i});" for i in range(1, 13)]
        con_css = contrast if contrast == contrast_d else f"light-dark({contrast}, {contrast_d})"
        lines += [f"    {P}accent-contrast: {con_css};", f"    {P}accent-text: var({P}{name}-{text_step});"]
        blocks.append((sel("accent"), lines))
        report.append(f"accent {hx}: light from {n_l['mix'][0]}+{n_l['mix'][1]}, dark from {n_d['mix'][0]}+{n_d['mix'][1]}"
                      + (f"; pinned light {pl}" if pl else "") + (f"; pinned dark {pd}" if pd else ""))
        report.append(f"  light step 9 = {light[8]}" + ("" if n_l["step9_exact"] or 9 in pl else "  (NOT the brand hex)")
                      + f" | dark step 9 = {dark[8]}" + ("" if n_d["step9_exact"] or 9 in pd else "  (NOT the brand hex)"))
        for mode, n, pins in (("light", n_l, pl), ("dark", n_d, pd)):
            if not n["step9_exact"] and 9 not in pins:
                notes.append(f"{mode} mode: {hx} is too close to the {mode} page background to work as a solid, "
                             f"so step 9 is a generated colour. Pin accent.pin.{mode}.9 to choose your own.")
        c9, c9d = K.wcag_contrast(contrast, light[8]), K.wcag_contrast(contrast_d, dark[8])
        report.append(f"  on-accent text: {contrast} {c9:.2f}:1 on light step 9, {contrast_d} {c9d:.2f}:1 on dark step 9")
        for mode, ratio, col in (("light", c9, contrast), ("dark", c9d, contrast_d)):
            if ratio < 4.5:
                notes.append(f"{mode} mode: on-accent text {col} reaches only {ratio:.2f}:1 on step 9 (WCAG AA needs 4.5:1 "
                             f"for normal text). Set accent.contrast.{mode}, or pin accent.pin.{mode}.9.")
        report.append(f"  light text step: {text_step} (step 11 worst case {worst11:.2f}:1, step 12 {worst12:.2f}:1)")
        if worst12 < 4.5:
            notes.append(f"light text step 12 reaches only {worst12:.2f}:1 in the worst case; pin a darker accent.pin.light.12.")
        dn = [data[f"primitives/{g}"][f"{g}-dark"][str(i)]["$value"] for g in GRAYS for i in (1, 2, 3)] + [dark[2], dark[3]]
        worst_d = min(K.wcag_contrast(dark[10], g) for g in dn)
        report.append(f"  dark text step 11 worst case {worst_d:.2f}:1")
        if worst_d < 4.5:
            notes.append(f"dark text step 11 reaches only {worst_d:.2f}:1 in the worst case; pin a lighter accent.pin.dark.11.")
    elif isinstance(accent, str):
        builtin("accent", "Accent color", accent)
        blocks.append((bundle("accent"), G.emit_set(res, f"semantic/accent-{accent}", "    ")))
        report.append(f"accent: built-in {accent} (data-brand only)")

    # ---------------- typography: families + weights (typeface axis), scale (brand only)
    typo = kit.get("typography") or {}
    imports = typo.get("import") or []
    fam = typo.get("families")
    type_lines, role_lines = [], []
    if isinstance(fam, dict):
        for slot in fam:
            if slot not in ("primary", "secondary", "mono"):
                raise KitError(f"typography.families: unknown slot {slot!r} (primary, secondary, mono)")
        base = data["semantic/typeface-system"]["family"]
        for slot in ("primary", "secondary", "mono"):
            type_lines.append(f"    {P}family-{slot}: {fam.get(slot, base[slot]['$value'])};")
        report.append("typeface: custom families " + ", ".join(sorted(fam)))
    elif isinstance(typo.get("typeface"), str):
        builtin("typography.typeface", "Typeface", typo["typeface"])
    weights = typo.get("weights") or {}
    for step, val in (weights.get("steps") or {}).items():
        if step not in WEIGHT_STEPS or not isinstance(val, int) or not 1 <= val <= 1000:
            raise KitError(f"typography.weights.steps: {step!r}: {val!r} (steps: {', '.join(WEIGHT_STEPS)}; value 1-1000)")
        type_lines.append(f"    {P}font-weight-{step}: {val};")
    for group, val in (weights.get("roles") or {}).items():
        if group not in ROLE_GROUPS:
            raise KitError(f"typography.weights.roles: unknown group {group!r} ({', '.join(ROLE_GROUPS)})")
        ref = f"var({P}font-weight-{val})" if val in WEIGHT_STEPS else val
        if not (val in WEIGHT_STEPS or (isinstance(val, int) and 1 <= val <= 1000)):
            raise KitError(f"typography.weights.roles.{group}: use a number 1-1000 or one of {', '.join(WEIGHT_STEPS)}")
        role_lines += [f"{P}{role}-weight: {ref};" for role in ROLE_GROUPS[group]]
    if weights:
        report.append("weights: " + json.dumps(weights))
    scoped = []                     # @scope blocks: (root selector, limit, inner selector, lines)
    if type_lines or role_lines:
        if isinstance(fam, dict) or weights:
            tsel = sel("typeface")
        blocks.append((tsel, type_lines + [f"    {l}" for l in role_lines]))
        if role_lines:
            # the core re-declares role weights on every nested [data-density];
            # re-apply the kit's inside its own scope (stops at another typeface/brand)
            scoped.append((f':is([data-typeface="{name}"], {brand}:not([data-typeface]))',
                           "[data-typeface], [data-brand]", "[data-density]", role_lines))
    elif isinstance(typo.get("typeface"), str):
        blocks.append((bundle("typeface"), G.emit_set(res, f"semantic/typeface-{typo['typeface']}", "    ")))
        report.append(f"typeface: built-in {typo['typeface']} (data-brand only)")

    # ---------------- recipe: built-in shape / depth / density choices (brand only)
    recipe = kit.get("recipe") or {}
    for axis in recipe:
        if axis not in ("shape", "depth", "density"):
            raise KitError(f"recipe: unknown axis {axis!r} (shape, depth, density)")
    if "shape" in recipe:
        builtin("recipe.shape", "Shape", recipe["shape"])
        blocks.append((bundle("shape"), G.shape_lines(res, recipe["shape"], "    ")))
    if "depth" in recipe:
        builtin("recipe.depth", "Depth", recipe["depth"])
        blocks.append((bundle("depth"), G.depth_shadow_lines(res, recipe["depth"], "    ")))
    density = recipe.get("density")
    if density:
        builtin("recipe.density", "Density", density)
    if recipe:
        report.append("recipe: " + ", ".join(f"{k}={v}" for k, v in recipe.items()))

    # ---------------- scale: the kit's base/ratio is its Comfortable scale;
    # Compact and Spacious keep MyCSS's own proportions to it unless given.
    scale = typo.get("scale")
    seeds = {}
    if scale:
        core = {d: (data[f"density/{d}"]["scale-base"]["$value"], data[f"density/{d}"]["scale-ratio"]["$value"])
                for d in ("compact", "comfortable", "spacious")}
        try:
            cb, cr = float(scale["base"]), float(scale["ratio"])
        except (KeyError, TypeError, ValueError):
            raise KitError("typography.scale: needs numeric base (px) and ratio")
        if not (8 <= cb <= 32 and 1.0 < cr <= 2.0):
            raise KitError("typography.scale: base 8-32, ratio above 1 and at most 2")
        fmt = lambda v: f"{round(v, 3):g}"
        for d in core:
            own = scale.get(d) or {}
            b = float(own["base"]) if "base" in own else (cb if d == "comfortable" else round(cb * core[d][0] / core["comfortable"][0] * 2) / 2)
            r = float(own["ratio"]) if "ratio" in own else (cr if d == "comfortable" else 1 + (cr - 1) * (core[d][1] - 1) / (core["comfortable"][1] - 1))
            seeds[d] = (fmt(b), fmt(r))
        report.append("scale (base/ratio): " + ", ".join(f"{d} {b}/{r}" for d, (b, r) in seeds.items()))
    seed_lines = lambda d: [f"{P}scale-base: {seeds[d][0]};", f"{P}scale-ratio: {seeds[d][1]};"]
    dens_lines = []
    if density:
        for s in G.theme_sets(data, "Density", density.capitalize()):
            dens_lines += G.emit_set(res, s, "    ")
        if seeds:
            dens_lines = [l for l in dens_lines if "scale-base" not in l and "scale-ratio" not in l]
    if seeds:
        dens_lines += [f"    {l}" for l in seed_lines(density or "comfortable")]
    if dens_lines:
        blocks.append((bundle("density"), dens_lines))
    if seeds:
        for d in seeds:
            blocks.append((f'{brand}[data-density="{d}"]', [f"    {l}" for l in seed_lines(d)]))
            scoped.append((brand, "[data-brand]", f'[data-density="{d}"]', seed_lines(d)))

    if not blocks:
        raise KitError("the kit defines nothing (accent, neutral, typography or recipe)")

    # ---------------- assemble
    label = kit.get("label", name)
    head = [f"/*! MyCSS brand kit: {label} ({name}) — generated by generate_brandkit.py from brandkits/{name}.json.",
            f"    Load after mycss.css. Switch on with data-brand=\"{name}\", or per axis with",
            f"    data-accent / data-gray / data-typeface=\"{name}\". Do not edit; regenerate.", ""]
    head += [f"    {l}" for l in report]
    if notes:
        head += ["", "    Check:"] + [f"    - {n}" for n in notes]
    head.append("*/")
    out = list(head)
    for url in imports:
        if not isinstance(url, str) or not url.startswith("https://") or any(c in url for c in '"\\\n'):
            raise KitError(f"typography.import: expected https URLs, got {url!r}")
        out.append(f'@import url("{url}");')
    out.append("@layer mycss.tokens {")
    if root:
        out += ["  :root {"] + root + ["  }"]
    for selector, lines in blocks:
        out += [f"  {selector} {{"] + lines + ["  }"]
    for scope_root, limit, inner, lines in scoped:
        out += [f"  @scope ({scope_root}) to ({limit}) {{", f"    {inner} {{"]
        out += [f"      {l}" for l in lines] + ["    }", "  }"]
    out.append("}")
    return "\n".join(out) + "\n", report, notes


def main():
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    res = G.Resolver(data)
    files = [Path(a) for a in sys.argv[1:]] or sorted(KITS.glob("*.json"))
    if not files:
        print(f"no kits in {KITS}")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    failed = 0
    for f in files:
        try:
            kit = json.loads(f.read_text(encoding="utf-8"))
            if kit.get("name") != f.stem:
                raise KitError(f'"name" must equal the file name ({f.stem!r})')
            css, report, notes = build_kit(kit, data, res)
        except (KitError, json.JSONDecodeError) as e:
            print(f"✗ {f.name}: {e}")
            failed += 1
            continue
        target = OUT / f"mycss.brandkit.{kit['name']}.css"
        target.write_text(css, encoding="utf-8")
        print(f"✓ {target.relative_to(ROOT)} ({len(css) // 1024} KB)")
        for line in report:
            print("   ", line)
        for n in notes:
            print("    ! " + n)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
