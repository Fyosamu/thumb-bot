"""Puzzle Chess series art - "PUZZLE CHESS PART N" above the king's crown.

    python bot/chess_series.py               # 16:9 + 9:16, commits the counter
    python bot/chess_series.py short --preview   # 9:16 only, no counter bump

* the crown row is DETECTED (bright rim light in the central column), so the
  wording is always placed above the actual head, never on top of it.
* the king is drawn fully opaque and sharpened over the text.
* the frame is continued around the square source with a blurred, darkened
  copy of itself -> no seams, no empty corners, no crop of the piece.
"""
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from poster_text import color_of, glow_line

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "..", "state", "chess_series.json")
SRC = r"C:\Users\USER\Desktop\yt_final\playground_test.jpg"
OUT_DIR = r"C:\Users\USER\Desktop\yt_final"
SEARCH = [OUT_DIR, r"C:\Users\USER\Desktop\yt_final"]     # frames may land in either
TARGETS = {"long": (1280, 720), "short": (720, 1280)}

# king geometry as a fraction of the square source (crown .. base)
HEAD_DEFAULT = 0.10
BASE_END = 0.87
KING_HALF_W = 0.17


def sharpen(img):
    img = ImageEnhance.Brightness(img).enhance(1.12)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Sharpness(img).enhance(1.6)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=100, threshold=3))


def head_row(img, frac=0.17):
    """top of the crown: first rows in the central column that are lit."""
    W, H = img.size
    strip = img.crop((int(W * (0.5 - frac)), 0, int(W * (0.5 + frac)), H)).convert("L")
    try:
        import numpy as np
        a = np.asarray(strip, dtype=np.uint8)
        rows = (a > 150).sum(axis=1)
        for y in range(H - 3):
            if rows[y:y + 3].min() >= 3:            # 3 bright px for 3 rows
                return y / H
        return HEAD_DEFAULT
    except Exception:                               # noqa: BLE001
        return HEAD_DEFAULT


def reflect_tile(strip, tw, th):
    """tile a narrow edge strip across an area, alternating mirror flips, so the
    wall keeps being wall and the marble keeps being marble - no blur, no dark."""
    sw, sh = strip.size
    out = Image.new(strip.mode, (tw, th))
    for yi, y in enumerate(range(0, th, sh)):
        for xi, x in enumerate(range(0, tw, sw)):
            t = strip
            if xi % 2:
                t = t.transpose(Image.FLIP_LEFT_RIGHT)
            if yi % 2:
                t = t.transpose(Image.FLIP_TOP_BOTTOM)
            out.paste(t, (x, y))
    return out


def extend(img, W, H, bh=None, ox=None, oy=None, fill=1.0):
    """fit the source in the frame (never crops the king) and COMPLETE the
    background with a mirrored continuation of the image's own edge."""
    sw, sh = img.size
    if bh is None:
        bh = int(sh * min(W / sw, H / sh) * fill)
    bw = int(sw * bh / sh)
    base = img.resize((bw, bh), Image.LANCZOS)

    ox = (W - bw) // 2 if ox is None else ox
    oy = (H - bh) // 2 if oy is None else oy

    # a narrow strip of the left edge - always wall + marble, never the king
    strip_w = max(8, min(abs(ox) or 8, bw, int(bw * (0.5 - KING_HALF_W - 0.04))))
    if strip_w <= 8:
        strip_w = max(8, int(bw * 0.12))
    strip = base.crop((0, 0, strip_w, bh))
    canvas = reflect_tile(strip, W, H)

    pad = max(4, int(min(W, H) * 0.05))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [ox + pad, oy + pad, ox + bw - pad, oy + bh - pad],
        radius=pad, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(pad * 1.1))

    mx0, my0 = max(0, ox), max(0, oy)
    mx1, my1 = min(W, ox + bw), min(H, oy + bh)
    if mx1 > mx0 and my1 > my0:
        canvas.paste(base.crop((mx0 - ox, my0 - oy, mx1 - ox, my1 - oy)),
                     (mx0, my0), mask.crop((mx0, my0, mx1, my1)))
    return canvas, (ox, oy, bw, bh)


def subject_front(canvas, base, rect, W, H, head_frac):
    """king fully opaque + sharpened, laid over the wording"""
    ox, oy, bw, bh = rect
    cx = ox + bw * 0.5
    cy = oy + (head_frac + BASE_END) * 0.5 * bh
    rx, ry = bw * KING_HALF_W, (BASE_END - head_frac) * 0.5 * bh

    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(min(W, H) * 0.035))

    L = base.convert("L")
    key = L.point(lambda v: 0 if v < 150 else min(255, (v - 150) * 4))
    keyf = Image.new("L", (W, H), 0)
    bx, by = max(0, ox), max(0, oy)
    keyf.paste(key.crop((bx - ox, by - oy,
                         min(bw, bx - ox + W - bx), min(bh, by - oy + H - by))), (bx, by))
    keyf = keyf.filter(ImageFilter.GaussianBlur(2))

    alpha = ImageChops.lighter(m, keyf)
    layer = canvas.copy()
    if ox + bw > 0 and oy + bh > 0:
        x0, y0 = max(0, ox), max(0, oy)
        x1, y1 = min(W, ox + bw), min(H, oy + bh)
        layer.paste(base.crop((x0 - ox, y0 - oy, x1 - ox, y1 - oy)), (x0, y0))
    return Image.composite(layer, canvas, alpha)


def next_part(kind, commit=True):
    try:
        data = json.load(open(STATE, encoding="utf-8"))
    except Exception:                               # noqa: BLE001
        data = {}
    n = int(data.get(kind, 0)) + 1
    if commit:
        data[kind] = n
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(data, open(STATE, "w", encoding="utf-8"), indent=1)
    return n


def peek():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:                               # noqa: BLE001
        return {}


def build(kind, commit=True, src=None, log=print):
    W, H = TARGETS[kind]
    n = next_part(kind, commit=commit)

    # only a re-generated frame (opt-in) may replace the source; normally the
    # exact picture the user gave us is used and merely completed
    if src is None and os.environ.get("CHESS_GEN_BG"):
        for d in SEARCH:
            cand = os.path.join(d, "chess_king_%s_bg.jpg" % kind)
            if os.path.exists(cand) and os.path.getsize(cand) > 50000:
                src = cand
                break
    src = src or SRC

    img = sharpen(Image.open(src).convert("RGB"))
    hf = head_row(img)
    full = abs((img.width / img.height) - (W / H)) < 0.03   # already the aspect

    if full:
        canvas = img.resize((W, H), Image.LANCZOS)
        rect = (0, 0, W, H)
        head = hf * H
    else:
        bh = int(H * (0.85 if kind == "long" else 0.62))
        oy = int(H * (0.32 if kind == "long" else 0.30) - hf * bh)
        canvas, rect = extend(img, W, H, bh=bh, oy=oy)
        head = oy + hf * rect[3]

    # wording above the crown, font sized to whatever room actually exists
    veil = Image.new("L", (W, H), 0)
    ImageDraw.Draw(veil).rectangle([0, 0, W, int(head - H * 0.02)], fill=85)
    veil = veil.filter(ImageFilter.GaussianBlur(H * 0.045))
    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [veil]))
    canvas = canvas.convert("RGB")

    avail = head - H * 0.05
    font = max(H * 0.05, min(H * 0.105, avail / 2.6))
    fh = font / 0.16                                   # glow_line takes the h arg
    y2 = int(head - H * 0.04 - font * 0.40)
    y1 = int(max(H * 0.05 + font * 0.40, y2 - font * 1.30))
    lay = canvas.convert("RGBA")
    GOLD = ((255, 244, 178), (255, 205, 74), (196, 130, 8))     # metallic gold
    glow_line(lay, "PUZZLE CHESS", color_of("gold"), y1, int(W * 0.9), fh,
              metal=GOLD)
    glow_line(lay, "PART %d" % n, color_of("gold"), y2, int(W * 0.9), fh,
              metal=GOLD)
    canvas = lay.convert("RGB")

    canvas = subject_front(canvas, img, rect, W, H, hf)

    out = os.path.join(OUT_DIR, "chess_part%d_%s.jpg" % (n, kind))
    os.makedirs(OUT_DIR, exist_ok=True)
    canvas.save(out, quality=95)
    log("saved %s | %dx%d | PART %d | src=%s | crown %.0f/%d | lines %d,%d"
        % (out, W, H, n, os.path.basename(src), head, H, y1, y2))
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    commit = "--preview" not in sys.argv
    kinds = [a for a in args if a in TARGETS] or list(TARGETS)
    print("counters:", peek(), "(%s)" % ("commit" if commit else "preview"))
    for k in kinds:
        build(k, commit=commit)
