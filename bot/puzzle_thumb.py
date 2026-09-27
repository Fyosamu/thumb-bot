# -*- coding: utf-8 -*-
"""Chess puzzle poster: the picture the user gave + a gold headline ABOVE it.

    python bot/puzzle_thumb.py --src=.. --mode=long [--preview] [--part=N]

  * the photo is NEVER cropped (contain + mirrored continuation of its own edge)
  * the "Made with AI" badge in the corner is painted out
  * headline "YOU CAN'T SOLVE THIS CHESS PUZZLE" + "PART N"
  * PART N lives in state/puzzle_series.json (long/short counted separately);
    a real run bumps the counter, --preview does not
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from poster_text import fit, font, glow_line, color_of     # noqa: E402

STATE = os.path.join(HERE, "..", "state", "puzzle_series.json")
OUT_DIR = r"C:\Users\USER\Desktop\yt_final"
MODES = {"long": (1280, 720), "short": (720, 1280)}
HEAD = "YOU CAN'T SOLVE THIS CHESS PUZZLE"
GOLD = ((255, 244, 178), (255, 205, 74), (196, 130, 8))


# ---------------------------------------------------------------- part counter
def next_part(kind, commit=True):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    data = {}
    if os.path.exists(STATE):
        try:
            data = json.load(open(STATE, encoding="utf-8"))
        except Exception:                                # noqa: BLE001
            data = {}
    n = int(data.get(kind, 0)) + 1
    if commit:
        data[kind] = n
        json.dump(data, open(STATE, "w", encoding="utf-8"), indent=1)
    return n


# ---------------------------------------------------------------- badge cut-out
def crop_badge(img, top_frac=0.25):
    """Find the white 'Made with AI' pill in the top-right and CUT the whole
    top band off the source so not a single pixel of it survives (no patching,
    no painting over - the user asked for a real crop)."""
    W, H = img.size
    px = img.load()
    y1 = 0
    for y in range(0, int(H * top_frac)):
        for x in range(int(W * 0.5), W, 3):
            r, g, b = px[x, y]
            if r > 235 and g > 235 and b > 235:
                y1 = max(y1, y)
                break
    if y1 <= 0:
        return img, 0
    cut = min(H - 8, y1 + int(H * 0.02))     # badge bottom + 2% margin
    return img.crop((0, cut, W, H)), cut


# ---------------------------------------------------------------- frame (no crop)
def _tile(strip, length, horizontal=True):
    """mirror-tile a narrow edge strip across a gap"""
    out = Image.new(strip.mode, (length, strip.height) if horizontal
                    else (strip.width, length))
    p = 0
    flip = False
    while p < length:
        t = strip.transpose(Image.FLIP_LEFT_RIGHT) if flip else strip
        if horizontal:
            out.paste(t, (p, 0))
        else:
            out.paste(t, (0, p))
        p += strip.width if horizontal else strip.height
        flip = not flip
    if horizontal:
        return out.crop((0, 0, length, strip.height))
    return out.crop((0, 0, strip.width, length))


def fit_frame(img, W, H):
    """contain the WHOLE photo, then continue its own edge over the leftover
    bands - no blur, no darkening, no cropping of the subject."""
    iw, ih = img.size
    s = min(W / iw, H / ih)
    bw, bh = max(8, int(iw * s)), max(8, int(ih * s))
    base = img.resize((bw, bh), Image.LANCZOS)
    ox, oy = (W - bw) // 2, (H - bh) // 2
    canvas = Image.new("RGB", (W, H))

    if ox > 0:                                    # side bands (wall / floor)
        sw = max(8, min(ox, int(bw * 0.12)))
        left = _tile(base.crop((0, 0, sw, bh)), ox, True)
        canvas.paste(left, (0, oy))
        right = _tile(base.crop((bw - sw, 0, bw, bh)), ox, True)
        canvas.paste(right, (ox + bw, oy))
    if oy > 0:                                    # top / bottom bands
        sh = max(8, min(oy, int(bh * 0.12)))
        top = _tile(base.crop((0, 0, bw, sh)), oy, False)
        canvas.paste(top, (ox, 0))
        bot = _tile(base.crop((0, bh - sh, bw, bh)), oy, False)
        canvas.paste(bot, (ox, oy + bh))

    pad = max(4, int(min(W, H) * 0.04))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [ox + pad, oy + pad, ox + bw - pad, oy + bh - pad], radius=pad, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(pad * 1.2))
    mx0, my0 = max(0, ox), max(0, oy)
    mx1, my1 = min(W, ox + bw), min(H, oy + bh)
    if mx1 > mx0 and my1 > my0:
        canvas.paste(base.crop((mx0 - ox, my0 - oy, mx1 - ox, my1 - oy)),
                     (mx0, my0), mask.crop((mx0, my0, mx1, my1)))
    return canvas, (ox, oy, bw, bh)


# ---------------------------------------------------------------- headline
def _wrapped(text, max_w, start, min_size=40):
    d = ImageDraw.Draw(Image.new("L", (8, 8)))
    size = start
    while size >= min_size:
        f = font(size)
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= max_w:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) == 1:
            return [(lines[0], f, size)]
        size -= 4
    f = font(min_size)
    return [(t, f, min_size) for t in [text]]


def headline(canvas, part, mode):
    W, H = canvas.size
    canvas = canvas.convert("RGBA")
    max_w = int(W * 0.96)                       # a bit wider -> bigger text

    # soft dark band across the top so gold always separates from the art
    veil = Image.new("L", (W, H), 0)
    ImageDraw.Draw(veil).rectangle([0, 0, W, int(H * 0.32)], fill=110)
    veil = veil.filter(ImageFilter.GaussianBlur(H * 0.055))
    canvas.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [veil]))

    start = int(H * (0.170 if mode == "long" else 0.116))
    lines = _wrapped(HEAD, max_w, start)
    lh = int(lines[0][2] * 1.30)
    block = lh * len(lines) + int(lines[0][2] * 1.15)      # + PART line
    y = int(H * 0.046)                                     # a touch lower
    cys = []
    for _ in lines:
        cys.append(y + lh // 2)
        y += lh
    part_size = int(lines[0][2] * 0.86)
    cys.append(y + int(part_size * 0.75))

    for (txt, f, size), cy in zip(lines, cys):
        h_arg = size / 0.16
        glow_line(canvas, txt.upper(), color_of("gold"), cy, max_w, h_arg,
                  metal=GOLD, stroke=max(3, int(size * 0.075)))
    glow_line(canvas, "PART %d" % part, color_of("gold"), cys[-1], max_w,
              part_size / 0.16, metal=GOLD, stroke=max(3, int(part_size * 0.075)))
    return canvas.convert("RGB")


def build(src, mode="long", part=None, preview=True, out=None, log=print):
    W, H = MODES[mode]
    n = part if part else next_part(mode, commit=not preview)
    img = Image.open(src).convert("RGB")
    img, cut = crop_badge(img)
    base, rect = fit_frame(img, W, H)
    base = headline(base, n, mode)
    out = out or os.path.join(OUT_DIR, "puzzle_part%d_%s.jpg" % (n, mode))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    base.save(out, quality=95)
    log("saved %s | %dx%d | PART %d | %s | badge CUT off (top %dpx removed)"
        % (out, W, H, n, os.path.basename(src), cut))
    return out


if __name__ == "__main__":
    kw = {}
    for a in sys.argv[1:]:
        if not a.startswith("--"):
            continue
        body = a[2:]
        if "=" in body:
            k, v = body.split("=", 1)
        else:
            k, v = body, "1"
        kw[k] = v
    src = kw.get("src") or os.path.join(HERE, "..", "..", "yt_final", "src",
                                        "pasted_1.jpg")
    mode = kw.get("mode", "long")
    build(src, mode, part=int(kw["part"]) if "part" in kw else None,
          preview="preview" in kw, out=kw.get("out"))
