# -*- coding: utf-8 -*-
"""Pinterest photo -> thumbnail: the photo is shown COMPLETE (never cropped),
a slim band on top holds the headline.

    python bot/pin_thumb.py --img=pin01.jpg --out=thumb.jpg --mode=long
                            --hook="WHY ANGER TAKES OVER"
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gold_thumb import load_font, wrap                      # noqa: E402
from glow_frame import (add_glow, accent_gradient, next_color,  # noqa: E402
                        part_color, metal_gradient, GOLD)

MODES = {"long": (1280, 720), "short": (720, 1280)}


def dominant(img, box=None):
    """Rough dominant colour of the photo -> used to fill the empty side space."""
    small = img.crop(box) if box else img
    small = small.convert("RGB").resize((32, 32), Image.BILINEAR)
    px = list(small.getdata())
    n = len(px)
    return tuple(sum(c[i] for c in px) // n for i in range(3))


def _darken(c, f=0.35):
    return tuple(int(v * f) for v in c)


def _veil(img, frac=0.40, strength=120):
    """Soft dark wash behind the headline so it reads on the photo, instead of
    a solid black bar cutting the picture in two (band-less mode)."""
    W, H = img.size
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle([0, 0, W, int(H * frac)], fill=strength)
    mask = mask.filter(ImageFilter.GaussianBlur(H * 0.07))
    out = img.convert("RGBA")
    out.alpha_composite(Image.merge("RGBA",
                                    [Image.new("L", (W, H), 0)] * 3 + [mask]))
    return out.convert("RGB")


def headline(canvas, text, accent, band_h, top=None, height=None, plate=225,
             metal=None):
    """Draw the hook (plus the optional "PART n" line) on black plates with the
    accent gradient on top.

    text      -> a string, or a list of strings (first = hook, rest = smaller)
    top/height-> vertical box the block must fit in.  Default is the slim top
                 band; with band_frac=0 the box sits ON the photo instead.
    metal     -> (top, mid, bot) gold stops: fill the glyphs with polished gold
                 instead of the accent colour (every chess video uses this).
    """
    W, H = canvas.size
    blocks = [text] if isinstance(text, str) else list(text)
    blocks = [b for b in blocks if b]
    if not blocks:
        return canvas.convert("RGB")
    height = band_h if height is None else height
    top = 0 if top is None else top
    room = height * 0.88
    gap = 6

    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    maxw = int(W * 0.90)

    def layout(size):
        rows = []
        for i, b in enumerate(blocks):
            ss = size if i == 0 else max(20, int(size * 0.66))
            f = load_font(ss)
            rows.append((wrap(probe, b, f, maxw), f, int(ss * 1.12)))
        return rows

    def total_h(rows):
        n = sum(len(r[0]) for r in rows)
        t = sum(len(r[0]) * r[2] for r in rows)
        return t + (gap * (n - 1) if n > 1 else 0)

    size = int(height * 0.42)
    rows = layout(size)
    while size >= 20 and total_h(rows) > room:
        size -= 3
        rows = layout(size)

    y = top + max(0, (height - total_h(rows)) // 2)
    y_top = y

    canvas = canvas.convert("RGBA")
    d = ImageDraw.Draw(canvas)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    for lines, font, lh_ in rows:
        for ln in lines:
            tw = int(probe.textlength(ln, font=font))
            bx = (W - tw) // 2
            bh = lh_ + 6
            d.rounded_rectangle([bx - 14, y - 3, bx + tw + 14, y + bh - 3],
                                radius=8, fill=(0, 0, 0, plate))
            md.text((bx, y), ln, font=font, fill=255)
            y += lh_ + gap
    y_bot = min(H, max(y_top + 1, y))
    if metal:
        # gold ramp laid exactly over the text block (not the whole canvas)
        canvas.paste(metal_gradient(W, y_bot - y_top, metal), (0, y_top),
                     mask.crop((0, y_top, W, y_bot)))
    else:
        canvas.paste(accent_gradient(W, H, accent), (0, 0), mask)
    return canvas.convert("RGB")


def make(img_path, out, mode="long", hook=None, accent=None, band_frac=0.20,
         part=None, metal=None):
    """Photo complete (never cropped) + headline.

    band_frac > 0 -> slim band above the photo.
    band_frac = 0 -> NO band: the headline is written on the photo itself.
    part          -> adds "PART n" and gives that part its own frame colour,
                     so the frame AND the headline change together every time.
    metal         -> gold stops: headline is filled with polished gold (every
                     chess video / short uses it), the frame keeps its own
                     colour for that part.
    """
    W, H = MODES[mode]
    src = Image.open(img_path).convert("RGB")
    sw, sh = src.size

    band = int(H * band_frac)
    area_w, area_h = W, H - band

    # photo fully visible: fit inside, never cropped
    s = min(area_w / sw, area_h / sh)
    nw, nh = max(1, int(sw * s)), max(1, int(sh * s))
    photo = src.resize((nw, nh), Image.LANCZOS)

    # fill the empty sides with the photo's own dominant colour (no blur/extend)
    dom = dominant(src)
    base = Image.new("RGB", (W, H), _darken(dom, 0.55))
    d = ImageDraw.Draw(base)
    if band:
        d.rectangle([0, 0, W, band], fill=_darken(dom, 0.30))
    px = (W - nw) // 2
    py = band + (area_h - nh) // 2
    # thin gold rule under the band
    base.paste(photo, (px, py))
    if band:
        d.rectangle([0, band - 3, W, band], fill=(224, 183, 87))

    if part:
        accent = part_color(part)[1]              # one colour per part
    elif accent is None:
        accent = next_color()[1]

    if hook is None:
        hook = os.path.splitext(os.path.basename(img_path))[0].upper()
    hook = hook.upper()
    blocks = [hook]
    if part:
        blocks.append("PART %d" % int(part))

    if band:
        base = headline(base, blocks, accent, band, top=0, height=band,
                        plate=225, metal=metal)
    else:
        base = _veil(base)                        # no black bar, just a wash
        base = headline(base, blocks, accent, 0, top=int(H * 0.03),
                        height=int(H * 0.34), plate=165, metal=metal)

    seed = (int(part or 0) * 977 + sum(ord(c) for c in hook)) & 0xFFFF
    base = add_glow(base, accent, strength=0.8, seed=seed)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    base.save(out, quality=95)
    return out, hook, accent


if __name__ == "__main__":
    kw = dict(a[len("--"):].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    img = kw["img"]
    out = kw.get("out") or img.rsplit(".", 1)[0] + "_thumb.jpg"
    acc = kw.get("accent")
    if isinstance(acc, str) and "," in acc:
        acc = tuple(int(x) for x in acc.split(","))
    part = kw.get("part")
    bf = kw.get("band_frac")
    p, h, c = make(img, out, kw.get("mode", "long"), kw.get("hook"), acc,
                   float(bf) if bf is not None else 0.20,
                   int(part) if part else None)
    print("saved", p, "|", h, "| rgb", c)
