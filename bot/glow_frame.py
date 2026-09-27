# -*- coding: utf-8 -*-
"""Fire-like glowing frame for thumbnails + matching text colour.

Every video / short gets its own colour (red, purple, green, ...) picked from a
rotation counter, so no two uploads look the same.

    from glow_frame import next_color, add_glow, accent_gradient
"""

import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "..", "state", "glow_color.json")

PALETTE = {
    "red":    (255, 46, 64),
    "purple": (176, 66, 255),
    "green":  (34, 230, 118),
    "blue":   (56, 140, 255),
    "orange": (255, 140, 30),
    "pink":   (255, 74, 186),
    "cyan":   (40, 226, 240),
    "yellow": (255, 214, 40),
    "magenta": (255, 60, 200),
    "lime":   (170, 255, 40),
}
ORDER = ["red", "purple", "green", "orange", "blue", "pink", "cyan", "yellow",
         "magenta", "lime"]


def next_color():
    """Rotating colour + name, remembered between runs (state/glow_color.json)."""
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    i = 0
    if os.path.exists(STATE):
        try:
            i = int(json.load(open(STATE, encoding="utf-8")).get("i", 0))
        except Exception:                              # noqa: BLE001
            i = 0
    name = ORDER[i % len(ORDER)]
    json.dump({"i": i + 1, "last": name}, open(STATE, "w", encoding="utf-8"))
    return name, PALETTE[name]


def color_by_seed(seed):
    """Deterministic colour (useful when re-rendering an existing video)."""
    name = ORDER[int(seed) % len(ORDER)]
    return name, PALETTE[name]


def _hue_shift(c, deg):
    import colorsys
    r, g, b = [max(0.0, min(255.0, v)) / 255.0 for v in c]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + (deg % 360) / 360.0) % 1.0
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return tuple(min(255, int(v * 255)) for v in (r, g, b))


def part_color(part):
    """ONE colour per part number -> the frame AND the headline change together
    every time a new video of the series is made (PART 1, 2, 3 ...).

    Parts 1-10 use the palette as-is; 11+ wrap around with a small hue shift so
    they are still different from the first ten.
    """
    i = max(0, int(part) - 1)
    name, c = color_by_seed(i)
    extra = (i // len(ORDER)) * 26
    if extra:
        c = _hue_shift(c, extra)
    return name, c


# the gold the user picked for EVERY chess video / short headline
GOLD = ((255, 244, 178), (255, 205, 74), (196, 130, 8))


def metal_gradient(w, h, stops=GOLD):
    """3-stop polished-gold vertical gradient used as the fill of the glyphs
    (light top -> saturated gold -> deep gold), same look as puzzle_thumb."""
    top, mid, bot = stops
    g = Image.new("RGB", (1, max(1, h)))
    px = g.load()
    for y in range(max(1, h)):
        t = y / max(1, h - 1)
        if t < 0.5:
            k = t / 0.5
            c = tuple(int(top[i] + (mid[i] - top[i]) * k) for i in range(3))
        else:
            k = (t - 0.5) / 0.5
            c = tuple(int(mid[i] + (bot[i] - mid[i]) * k) for i in range(3))
        px[0, y] = c
    return g.resize((max(1, w), max(1, h)))


def _ring(w, h, thick):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=18, outline=255, width=thick)
    d.rectangle([0, 0, w - 1, h - 1], outline=255, width=1)
    return m


def _flame_noise(w, h, thick, rng):
    """Flickering tongues along the border -> looks like fire, not a flat line."""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    n = int((w + h) * 0.55)
    for _ in range(n):
        side = rng.random()
        if side < 0.5:
            x = rng.uniform(0, w)
            y = rng.choice([rng.uniform(-6, thick), rng.uniform(h - thick, h + 6)])
        else:
            x = rng.choice([rng.uniform(-6, thick), rng.uniform(w - thick, w + 6)])
            y = rng.uniform(0, h)
        r = rng.uniform(3, 14)
        d.ellipse([x - r, y - r, x + r, y + r], fill=rng.randint(140, 255))
    return m


def add_glow(img, color, strength=1.0, seed=0):
    """Fire-like halo around the edge, tinted with `color` (RGB)."""
    w, h = img.size
    rng = random.Random(seed or (w * 31 + h))
    out = img.convert("RGB")

    thick = max(6, int(min(w, h) * 0.035))
    ring = _ring(w, h, thick)
    tongues = _flame_noise(w, h, thick, rng)

    layers = [
        (ring.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.012))), 1.00),
        (ring.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.045))), 0.75),
        (ring.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.10))), 0.45),
        (tongues.filter(ImageFilter.GaussianBlur(6)), 0.85),
        (tongues.filter(ImageFilter.GaussianBlur(18)), 0.55),
    ]

    for mask, k in layers:
        r, g, b = color
        tint = Image.new("RGB", (w, h), (int(r * k), int(g * k), int(b * k)))
        out = Image.blend(out, Image.new("RGB", (w, h), (0, 0, 0)), 0.0)
        glow = Image.composite(tint, Image.new("RGB", (w, h), (0, 0, 0)), mask)
        out = _screen(out, glow, strength)

    # bright inner core so the edge reads as a hot line
    core = _ring(w, h, max(2, thick // 3)).filter(ImageFilter.GaussianBlur(1.5))
    r, g, b = color
    hot = Image.composite(Image.new("RGB", (w, h), (min(255, r + 90), min(255, g + 90),
                                                    min(255, b + 90))),
                          Image.new("RGB", (w, h), (0, 0, 0)), core)
    out = _screen(out, hot, strength * 0.9)
    return out


def _screen(a, b, strength=1.0):
    """Screen blend (a + b - a*b) with an overall strength multiplier."""
    from PIL import ImageChops
    if strength != 1.0:
        b = Image.eval(b, lambda v: int(v * strength))
    return ImageChops.screen(a, b)


def accent_gradient(w, h, color, name=""):
    """Vertical gradient for text: readable (darker) top -> colour -> deep bottom."""
    top = tuple(min(255, int(c * 0.82) + 38) for c in color)
    mid = tuple(int(c * 0.90) for c in color)
    bot = tuple(int(c * 0.40) for c in color)
    g = Image.new("RGB", (w, h))
    px = g.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.5:
            k = t / 0.5
            c = tuple(int(top[i] + (mid[i] - top[i]) * k) for i in range(3))
        else:
            k = (t - 0.5) / 0.5
            c = tuple(int(mid[i] + (bot[i] - mid[i]) * k) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return g


def glow_text_mask(img, mask, color, strength=1.6, blur=10):
    """Soft coloured halo behind the letters so text matches the frame."""
    halo = mask.filter(ImageFilter.GaussianBlur(blur))
    halo = halo.point(lambda v: min(255, int(v * strength)))
    tint = Image.new("RGB", img.size, color)
    g = Image.composite(tint, Image.new("RGB", img.size, (0, 0, 0)), halo)
    return _screen(img, g, 1.0)


if __name__ == "__main__":
    print("palette:", list(PALETTE))
    print("next:", next_color())
