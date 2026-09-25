"""Puzzle Chess series art - "PUZZLE CHESS PART N" behind the king.

    python bot/chess_series.py            # both formats, commit (increments)
    python bot/chess_series.py long       # 16:9 only
    python bot/chess_series.py short      # 9:16 only
    python bot/chess_series.py long --preview   # render next number, no increment

* N counts uploaded longs and shorts separately (state/chess_series.json).
* the square source is extended into the target aspect with mirrored, blurred,
  darkened wings (outpaint), so the king never gets cropped.
* the text is drawn FIRST and the bright parts of the photo (the king and the
  highlights) are keyed back on top, so the wording sits *behind* the piece.
"""
import json
import os
import sys

from PIL import Image, ImageChops, ImageFilter

from poster_text import color_of, glow_line

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "..", "state", "chess_series.json")
SRC = r"C:\Users\USER\Desktop\yoo\playground_test.jpg"
OUT_DIR = r"C:\Users\USER\Desktop\yoo"
TARGETS = {"long": (1280, 720), "short": (720, 1280)}


def peek():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:                       # noqa: BLE001
        return {}


def next_part(kind, commit=True):
    data = peek()
    n = int(data.get(kind, 0)) + 1
    if commit:
        data[kind] = n
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(data, open(STATE, "w", encoding="utf-8"), indent=1)
    return n


def _wing(strip, dark=0.55, blur=7):
    """mirrored continuation of an edge strip: seamless at the seam, then
    blurred + darkened so it reads as background depth."""
    wing = strip.transpose(Image.FLIP_LEFT_RIGHT).filter(ImageFilter.GaussianBlur(blur))
    return Image.eval(wing, lambda v: int(v * dark))


def extend(img, W, H):
    """fit the square source fully inside WxH and outpaint the rest."""
    sw, sh = img.size
    s = min(W / sw, H / sh)
    base = img.resize((int(sw * s), int(sh * s)), Image.LANCZOS)
    bw, bh = base.size
    canvas = Image.new("RGB", (W, H), (8, 9, 12))
    ox, oy = (W - bw) // 2, (H - bh) // 2

    if bw < W:                                     # wings left/right
        need = ox
        left = _wing(base.crop((0, 0, min(need, bw), bh)))
        right = _wing(base.crop((bw - min(need, bw), 0, bw, bh)))
        canvas.paste(left, (0, oy))
        canvas.paste(right, (W - right.width, oy))
    if bh < H:                                     # wings top/bottom
        need = oy
        top = _wing(base.crop((0, 0, bw, min(need, bh)))).transpose(Image.ROTATE_180)
        bot = _wing(base.crop((0, bh - min(need, bh), bw, bh))).transpose(Image.ROTATE_180)
        canvas.paste(top, (ox, 0))
        canvas.paste(bot, (ox, H - bot.height))

    # feather the seams so the paste lines disappear
    soft = canvas.copy()
    soft.paste(base, (ox, oy))
    canvas = Image.blend(canvas, soft, 0.0)
    mask = Image.new("L", (W, H), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(mask)
    pad = int(min(W, H) * 0.04)
    d.rectangle([ox + pad, oy + pad, ox + bw - pad, oy + bh - pad], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(pad * 1.2))
    canvas.paste(soft, (0, 0), mask)
    return canvas, (ox, oy, bw, bh)


def key_subject_back(canvas, base, rect):
    """put the bright parts of the photo (the king) in front of the text"""
    ox, oy, bw, bh = rect
    L = base.convert("L")
    m = L.point(lambda v: 0 if v < 85 else min(255, (v - 85) * 5))
    m = m.filter(ImageFilter.GaussianBlur(2))
    canvas.paste(base, (ox, oy), m)
    return canvas


def build(kind, commit=True, src=SRC, log=print):
    W, H = TARGETS[kind]
    n = next_part(kind, commit=commit)
    img = Image.open(src).convert("RGB")
    canvas, rect = extend(img, W, H)

    canvas = canvas.convert("RGBA")
    cy1, cy2 = int(H * 0.44), int(H * 0.60)
    glow_line(canvas, "PUZZLE CHESS", color_of("gold"), cy1, int(W * 0.92), H)
    glow_line(canvas, "PART %d" % n, color_of("cyan"), cy2, int(W * 0.92), H)
    canvas = canvas.convert("RGB")

    ox, oy, bw, bh = rect
    canvas = key_subject_back(canvas, img.resize((bw, bh), Image.LANCZOS), rect)

    out = os.path.join(OUT_DIR, "chess_part%d_%s.jpg" % (n, kind))
    os.makedirs(OUT_DIR, exist_ok=True)
    canvas.save(out, quality=95)
    log("saved %s | %dx%d | PART %d (%s)" % (out, W, H, n, kind))
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    commit = "--preview" not in sys.argv
    kinds = [a for a in args if a in TARGETS] or list(TARGETS)
    print("counters:", peek(), "(%s)" % ("commit" if commit else "preview"))
    for k in kinds:
        build(k, commit=commit)
