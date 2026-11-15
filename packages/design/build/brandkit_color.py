"""Colour maths for MyCSS brand kits: one brand hex -> a 12-step ramp.

A Python port of the method behind Radix's custom-palette tool
(generateRadixColors): find the two closest built-in Radix scales, blend
them, take the brand colour's hue and chroma, keep the scale's lightness
curve, then put the exact brand colour at step 9. Differences from the
original: scales are blended in OKLab (the original blends in CIE Lab), and
the page background is fixed (white in light, #111111 in dark).
No dependencies.
"""
import math

# ---------- sRGB <-> OKLab / OKLCH

def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return "#" + "".join(f"{round(min(1, max(0, c)) * 255):02x}" for c in rgb)

def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (abs(c) ** (1 / 2.4)) - 0.055 if c > 0 else 12.92 * c

def rgb_to_oklab(rgb):
    r, g, b = (_lin(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)

def oklab_to_rgb(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(_gam(c) for c in (r, g, bb))

def lab_to_lch(lab):
    L, a, b = lab
    return (L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)

def lch_to_lab(lch):
    L, C, H = lch
    return (L, C * math.cos(math.radians(H)), C * math.sin(math.radians(H)))

def hex_to_lch(h):
    return lab_to_lch(rgb_to_oklab(hex_to_rgb(h)))

def lch_to_hex(lch):
    """OKLCH -> sRGB hex; out-of-gamut colours lose chroma, never L or hue."""
    L, C, H = lch
    L = min(1, max(0, L))
    ok = lambda rgb: all(-1e-4 <= c <= 1 + 1e-4 for c in rgb)
    rgb = oklab_to_rgb(lch_to_lab((L, C, H)))
    if not ok(rgb):
        lo, hi = 0.0, C
        for _ in range(24):
            mid = (lo + hi) / 2
            if ok(oklab_to_rgb(lch_to_lab((L, mid, H)))):
                lo = mid
            else:
                hi = mid
        rgb = oklab_to_rgb(lch_to_lab((L, lo, H)))
    return rgb_to_hex(rgb)

def delta_e(lch1, lch2):
    a, b = lch_to_lab(lch1), lch_to_lab(lch2)
    return math.dist(a, b)

# ---------- contrast

def wcag_contrast(hex1, hex2):
    def lum(h):
        r, g, b = (_lin(c) for c in hex_to_rgb(h))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    a, b = sorted((lum(hex1), lum(hex2)), reverse=True)
    return (a + 0.05) / (b + 0.05)

def apca(bg_hex, txt_hex):
    """APCA-W3 Lc (0.98G-4g constants), background first."""
    def y(h):
        r, g, b = (c ** 2.4 for c in hex_to_rgb(h))
        v = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
        return v if v >= 0.022 else v + (0.022 - v) ** 1.414
    yb, yt = y(bg_hex), y(txt_hex)
    if abs(yb - yt) < 0.0005:
        return 0.0
    if yb > yt:
        c = (yb ** 0.56 - yt ** 0.57) * 1.14
        return 0.0 if c < 0.1 else (c - 0.027) * 100
    c = (yb ** 0.65 - yt ** 0.62) * 1.14
    return 0.0 if c > -0.1 else (c + 0.027) * 100

# ---------- cubic-bezier easing (for the dark-mode lightness transpose)

def bezier(x1, y1, x2, y2):
    def f(t, p1, p2):
        return 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3
    def ease(x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(40):
            t = (lo + hi) / 2
            if f(t, x1, x2) < x: lo = t
            else: hi = t
        return f((lo + hi) / 2, y1, y2)
    return ease

def transpose_start(to, arr, curve):
    fn, last, diff = bezier(*curve), len(arr) - 1, arr[0] - to
    return [n - diff * fn(1 - i / last) for i, n in enumerate(arr)]

LIGHT_EASING, DARK_EASING = (0, 2, 0, 2), (1, 0, 1, 0)

# ---------- the scale

def scale_from_color(source, scales, gray_names, background):
    """source/background: OKLCH; scales: {name: [12 OKLCH]} -> [12 OKLCH]."""
    ranked = sorted(((delta_e(source, c), name) for name, sc in scales.items() for c in sc))
    closest, seen = [], set()
    for dist, name in ranked:
        if name not in seen:
            seen.add(name); closest.append((dist, name))
    all_gray = all(n in gray_names for _, n in closest)
    if not all_gray and closest[0][1] in gray_names:
        while len(closest) > 1 and closest[1][1] in gray_names:
            closest.pop(1)
    (b, name_a), (a, name_b) = closest[0], closest[1]
    sa, sb = scales[name_a], scales[name_b]
    # how far towards scale B the source sits (triangle A-B-source)
    ia = min(range(12), key=lambda i: delta_e(source, sa[i]))
    ib = min(range(12), key=lambda i: delta_e(source, sb[i]))
    c = delta_e(sa[ia], sb[ib])
    ratio = 0.0
    if a > 1e-9 and b > 1e-9 and c > 1e-9:
        cos_a = max(-1, min(1, (b * b + c * c - a * a) / (2 * b * c)))
        cos_b = max(-1, min(1, (a * a + c * c - b * b) / (2 * a * c)))
        sin_a, sin_b = math.sin(math.acos(cos_a)), math.sin(math.acos(cos_b))
        if sin_a > 1e-9 and sin_b > 1e-9 and abs(cos_b) > 1e-9:
            ratio = max(0.0, (cos_a / sin_a) / (cos_b / sin_b)) * 0.5
    ratio = min(1.0, ratio)
    scale = []
    for i in range(12):
        la, lb = lch_to_lab(sa[i]), lch_to_lab(sb[i])
        scale.append(list(lab_to_lch(tuple(x + (y - x) * ratio for x, y in zip(la, lb)))))
    base = min(scale, key=lambda col: delta_e(source, col))
    if base[1] < 1e-6:
        ratio_c = 0.0 if source[1] < 1e-6 else 1.0
    else:
        ratio_c = source[1] / base[1]
    for col in scale:
        col[1] = min(source[1] * 1.5, col[1] * ratio_c)
        col[2] = source[2]
    bg_l = max(0, min(1, background[0]))
    if scale[0][0] > 0.5:                                   # light
        new = transpose_start(bg_l, [1.0] + [c_[0] for c_ in scale], LIGHT_EASING)[1:]
    else:                                                   # dark
        ease = list(DARK_EASING)
        ratio_l = bg_l / scale[0][0] if scale[0][0] else 1
        if ratio_l > 1:
            max_ratio = 1.5
            meta = (ratio_l - 1) * (max_ratio / (max_ratio - 1))
            ease = [0 if ratio_l > max_ratio else max(0, e * (1 - meta)) for e in ease]
        new = transpose_start(bg_l, [c_[0] for c_ in scale], ease)
    for col, l in zip(scale, new):
        col[0] = l
    return scale, (name_a, name_b, ratio)

def text_on(color_hex):
    """Radix getTextColor: white unless white-on-colour is too weak (|Lc| < 40)."""
    if abs(apca("#ffffff", color_hex)) < 40:
        L, C, H = hex_to_lch(color_hex)
        return lch_to_hex((0.25, max(0.08 * C, 0.04), H))
    return "#ffffff"

def hover_of(step9, scale):
    L, C, H = step9
    new_l = L - 0.03 / (L + 0.1) if L > 0.4 else L + 0.03 / (L + 0.1)
    new_c = C * 0.93 if L > 0.4 else C
    hover = [new_l, new_c, H]
    donor = min(scale, key=lambda col: delta_e(hover, col))
    hover[1], hover[2] = donor[1], donor[2]
    return hover

def accent_scale(hex_, scales, gray_names, background_hex):
    """-> (12 hex steps, contrast hex, notes dict). Step 9 is the brand hex
    unless it would vanish into the page background (see below)."""
    src, bg = hex_to_lch(hex_), hex_to_lch(background_hex)
    scale, mix = scale_from_color(src, scales, gray_names, bg)
    notes = {"mix": mix, "step9_exact": True}
    # Radix swaps in the generated step 9 when the colour is within 0.25 of
    # the page background. A brand kit promises the exact brand colour, so
    # MyCSS only does it when the colour would vanish into the page: closer
    # than 0.10 on white, 0.20 on the dark background. Pin a step to override.
    if delta_e(src, scale[0]) < (0.10 if scale[0][0] > 0.5 else 0.20):
        notes["step9_exact"] = False
        step9 = list(scale[8])
    else:
        step9 = list(src)
    scale[8] = step9
    scale[9] = hover_of(step9, scale)
    cap = max(scale[8][1], scale[7][1])
    scale[10][1] = min(cap, scale[10][1])
    scale[11][1] = min(cap, scale[11][1])
    hexes = [lch_to_hex(c) for c in scale]
    if notes["step9_exact"]:
        hexes[8] = "#" + hex_.strip().lstrip("#").lower() if len(hex_.strip().lstrip("#")) == 6 else rgb_to_hex(hex_to_rgb(hex_))
    return hexes, text_on(hexes[8]), notes

def gray_scale(hex_, gray_scales, background_hex):
    src, bg = hex_to_lch(hex_), hex_to_lch(background_hex)
    scale, mix = scale_from_color(src, gray_scales, set(gray_scales), bg)
    return [lch_to_hex(c) for c in scale], {"mix": mix}

# ---------- alpha twins
# The most transparent colour that composites back to exactly the solid step
# on the reference background (same idea as Radix's alpha scales).

def alpha_of(target_hex, background_hex):
    t = [round(c * 255) for c in hex_to_rgb(target_hex)]
    b = [round(c * 255) for c in hex_to_rgb(background_hex)]
    if t == b:
        return "#00000000"
    need = 0.0
    for tc, bc in zip(t, b):
        if tc > bc: need = max(need, (tc - bc) / (255 - bc))
        elif tc < bc: need = max(need, (bc - tc) / bc)
    for a255 in range(max(1, math.ceil(need * 255 - 1e-9)), 256):
        A, out = a255 / 255, []
        for tc, bc in zip(t, b):
            ideal = (tc - bc * (1 - A)) / A
            hit = next((v for v in (round(ideal), math.floor(ideal), math.ceil(ideal))
                        if 0 <= v <= 255 and round(bc * (1 - A) + v * A) == tc), None)
            if hit is None:
                break
            out.append(hit)
        else:
            body = "".join(f"{v:02x}" for v in out)
            return "#" + body + (f"{a255:02x}" if a255 < 255 else "")
    return "#" + "".join(f"{v:02x}" for v in t)

def blend(alpha_hex, background_hex):
    h = alpha_hex.lstrip("#")
    fg = [int(h[i:i + 2], 16) for i in (0, 2, 4)]; a = int(h[6:8] or "ff", 16) / 255
    bg = [round(c * 255) for c in hex_to_rgb(background_hex)]
    return "#" + "".join(f"{round(b_ * (1 - a) + f * a):02x}" for f, b_ in zip(fg, bg))
