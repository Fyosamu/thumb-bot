"""Chess player art: clear, bright subject + hook text on top, 16:9 and 9:16.

    python bot/player_art.py            # both formats

The generated photo is sharpened/brightened first so the player stays fully
readable, the hook sits only in the empty top band (veil never touches him),
and the short version is produced by outpainting the 16:9 frame to 9:16.
"""
import os
import sys

from PIL import Image, ImageEnhance, ImageFilter

from chess_series import extend
from poster_text import color_of, glow_line

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:\Users\USER\Desktop\yt_final\chess_player_bg.jpg"
OUT_DIR = r"C:\Users\USER\Desktop\yt_final"
TARGETS = {"long": (1280, 720), "short": (720, 1280)}
LINES = [("HE SACRIFICED HIS QUEEN", "gold"),
         ("WATCH WHAT HAPPENS NEXT", "cyan")]


def sharpen(img):
    img = ImageEnhance.Brightness(img).enhance(1.14)
    img = ImageEnhance.Contrast(img).enhance(1.10)
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=3))


def build(kind, src=SRC, out=None, lines=LINES, log=print):
    W, H = TARGETS[kind]
    img = sharpen(Image.open(src).convert("RGB"))
    canvas, rect = extend(img, W, H)

    # veil ONLY over the empty top band, blurred so it never dims the subject
    band = int(H * (0.34 if kind == "long" else 0.30))
    veil = Image.new("L", (W, H), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(veil).rectangle([0, 0, W, band], fill=105)
    veil = veil.filter(ImageFilter.GaussianBlur(H * 0.05))
    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [veil]))

    ys = (0.13, 0.26) if kind == "long" else (0.11, 0.22)
    for (text, col), y in zip(lines, ys):
        glow_line(canvas, text, color_of(col), int(H * y), int(W * 0.94), H)

    out = out or os.path.join(OUT_DIR, "chess_player%s.jpg" % ("" if kind == "long" else "_short"))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    canvas.convert("RGB").save(out, quality=96)
    log("saved %s | %dx%d" % (out, W, H))
    return out


if __name__ == "__main__":
    kinds = [a for a in sys.argv[1:] if a in TARGETS] or list(TARGETS)
    for k in kinds:
        build(k)
