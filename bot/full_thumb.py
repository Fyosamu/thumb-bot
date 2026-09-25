# -*- coding: utf-8 -*-
"""Text on top of a 100% GitHub-generated picture (no photo-in-photo).

The prompt asks the model to leave the TOP THIRD empty, so the hook simply
goes there: full-bleed image, headline above it, subject untouched.

    python bot/full_thumb.py --bg=..._bg.jpg --out=..._thumb.jpg --mode=long
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gold_thumb import load_font, wrap                      # noqa: E402
from glow_frame import add_glow, accent_gradient, next_color  # noqa: E402

MODES = {"long": (1280, 720), "short": (720, 1280)}
HOOKS = [
    "WHY ANGER TAKES OVER YOUR BRAIN",
    "WHAT ANGER DOES TO YOUR BODY",
    "THE SCIENCE OF RAGE",
    "THIS IS WHY YOU CAN'T CALM DOWN",
]


def _cover(img, w, h):
    iw, ih = img.size
    s = max(w / iw, h / ih)
    nw, nh = int(iw * s + .5), int(ih * s + .5)
    img = img.resize((nw, nh), Image.LANCZOS)
    return img.crop(((nw - w) // 2, (nh - h) // 2,
                     (nw - w) // 2 + w, (nh - h) // 2 + h))


def headline(canvas, text, accent, top=0.045, room=0.34):
    """Gold/accent headline in the empty top band of the generated frame."""
    W, H = canvas.size
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    maxw = int(W * (0.86 if W > H else 0.90))
    size = int(W * (0.072 if W > H else 0.115))
    while size >= 26:
        f = load_font(size)
        lines = wrap(probe, text, f, maxw)
        if len(lines) * int(size * 1.12) <= H * room:
            break
        size -= 4
    font = load_font(size)
    lines = wrap(probe, text, font, maxw)

    lh, gap, padx, pady = int(size * 1.12), 8, 22, 11
    y = int(H * top)
    boxes = []
    for ln in lines:
        tw = int(probe.textlength(ln, font=font))
        bw, bh = tw + padx * 2, lh + pady * 2
        boxes.append((ln, tw, bw, bh))
        y += bh + gap
    y -= gap

    # soft dark wash over the band so text always separates from the art
    wash = Image.new("L", (W, H), 0)
    ImageDraw.Draw(wash).rectangle([0, 0, W, int(y + H * 0.06)], fill=115)
    wash = wash.filter(ImageFilter.GaussianBlur(H * 0.05))
    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [wash]))

    sh = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sh)
    yy = int(H * top)
    for _, _, bw, bh in boxes:
        sd.rounded_rectangle([(W - bw) // 2 + 6, yy + 8, (W - bw) // 2 + bw + 6,
                              yy + bh + 8], radius=10, fill=255)
        yy += bh + gap
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    canvas.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [sh]))

    d = ImageDraw.Draw(canvas)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    yy = int(H * top)
    for ln, tw, bw, bh in boxes:
        bx = (W - bw) // 2
        d.rounded_rectangle([bx, yy, bx + bw, yy + bh], radius=10, fill=(0, 0, 0))
        md.text((bx + padx, yy + pady - int(lh * 0.14)), ln, font=font, fill=255)
        yy += bh + gap
    canvas.paste(accent_gradient(W, H, accent), (0, 0), mask)
    return canvas.convert("RGB")


def make(bg, out, mode="long", hook=None, accent=None):
    W, H = MODES[mode]
    img = Image.open(bg).convert("RGB")
    # already the right shape -> keep it 100% untouched (never squashed)
    if abs(img.width / img.height - W / H) < 0.02:
        base = img.resize((W, H), Image.LANCZOS)
    else:
        base = _cover(img, W, H)
    if hook is None:
        hook = HOOKS[abs(hash(bg)) % len(HOOKS)]
    if accent is None:
        accent = next_color()[1]
    base = headline(base, hook.upper(), accent)
    base = add_glow(base, accent, strength=1.0, seed=abs(hash(hook)) & 0xFFFF)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    base.save(out, quality=95)
    return out, hook, accent


if __name__ == "__main__":
    kw = dict(a[len("--"):].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    bg = kw.get("bg") or r"C:\Users\USER\Desktop\yt_final\sci_anger_long_bg.jpg"
    out = kw.get("out") or bg.replace("_bg", "_thumb")
    p, h, c = make(bg, out, kw.get("mode", "long"), kw.get("hook"), kw.get("accent"))
    print("saved", p, "|", h, "| rgb", c)
