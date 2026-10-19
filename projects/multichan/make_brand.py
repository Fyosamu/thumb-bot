# -*- coding: utf-8 -*-
"""Channel branding: 2560x1440 banners + 800x800 profile pictures for
every multichan channel, from its palette and name.

    python make_brand.py all        # every channel
    python make_brand.py 5          # just channel 5

Output: projects/multichan/brands/<id>_banner.jpg, <id>_profile.jpg
(these never enter the main repo - they ship to the public brands repo
so the YouTube API can pull them by URL).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
REG = json.loads((HERE / "channels.json").read_text(encoding="utf-8"))
BRANDS = HERE / "brands"

F = "C:/Windows/Fonts/arialbd.ttf"
FR = "C:/Windows/Fonts/arial.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def vgrad(w: int, h: int, top: tuple, bot: tuple) -> Image.Image:
    strip = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        strip.putpixel((0, y), tuple(
            int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return strip.resize((w, h))


def fit_font(draw: ImageDraw.ImageDraw, text: str, path: str,
             max_w: int, start: int, min_size: int = 30) -> ImageFont.FreeTypeFont:
    size = start
    while size > min_size:
        f = font(path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 6
    return font(path, min_size)


def banner(e: dict) -> Image.Image:
    W, H = 2560, 1440
    bg, accent, band = (tuple(c) for c in e["palette"])
    img = vgrad(W, H, bg, tuple(min(255, int(c * 1.9) + 6) for c in bg))
    d = ImageDraw.Draw(img, "RGBA")

    # diagonal accent streaks, lower-left energy
    for i, xoff in enumerate((-400, 150, 700)):
        d.polygon([(xoff, H), (xoff + 380, H), (xoff + 900, 0),
                   (xoff + 520, 0)],
                  fill=(*accent, 26 if i != 1 else 44))

    # soft glow blob behind the title
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W // 2 - 760, H // 2 - 340, W // 2 + 760, H // 2 + 340],
               fill=(*accent, 60))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    d = ImageDraw.Draw(img, "RGBA")

    # safe area: 1546x423 centered (YouTube crops outside it)
    sw, sh = 1546, 423
    sx, sy = (W - sw) // 2, (H - sh) // 2

    tag = e["tagline"].upper()
    d.text((W // 2, sy + 34), tag,
           font=font(FR, 44), fill=(*accent, 255), anchor="mm")

    name_f = fit_font(d, e["name"], F, sw - 60, 150)
    ny = sy + 158
    d.text((W // 2, ny), e["name"], font=name_f, fill=(255, 255, 255, 255),
           anchor="mm")

    # accent underline
    nw = d.textlength(e["name"], font=name_f)
    d.rounded_rectangle([W // 2 - nw // 2, ny + 92, W // 2 + nw // 2,
                         ny + 110], radius=9, fill=(*accent, 255))

    cat = e["category_en"].upper()
    d.text((W // 2, sy + 330), cat, font=font(FR, 40),
           fill=(235, 238, 245, 210), anchor="mm")
    d.text((W // 2, H - 66), "MINDSERIES", font=font(FR, 34),
           fill=(255, 255, 255, 110), anchor="mm")
    return img.convert("RGB")


def profile(e: dict) -> Image.Image:
    S = 800
    bg, accent, _ = (tuple(c) for c in e["palette"])
    img = vgrad(S, S, tuple(min(255, int(c * 2.2) + 8) for c in bg), bg)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([40, 40, S - 40, S - 40], outline=(*accent, 255), width=14)
    d.ellipse([70, 70, S - 70, S - 70], outline=(*accent, 70), width=3)

    words = [w for w in e["name"].split() if w[0].isalpha()][:2]
    mono = "".join(w[0] for w in words).upper()
    f = fit_font(d, mono, F, 420, 300)
    d.text((S // 2, S // 2 - 40), mono, font=f, fill=(255, 255, 255, 255),
           anchor="mm")
    d.text((S // 2, S // 2 + 150), e["tagline"].upper()[:34],
           font=font(FR, 34), fill=(*accent, 255), anchor="mm")
    return img.convert("RGB")


def main() -> int:
    ids = [c["id"] for c in REG["channels"]]
    if len(sys.argv) > 1 and sys.argv[1] != "all":
        ids = [int(sys.argv[1])]
    BRANDS.mkdir(parents=True, exist_ok=True)
    n = 0
    for e in REG["channels"]:
        if e["id"] not in ids:
            continue
        banner(e).save(BRANDS / f"{e['id']}_banner.jpg", quality=90)
        profile(e).save(BRANDS / f"{e['id']}_profile.jpg", quality=90)
        n += 1
    print(f"brands rendered: {n} channels -> {BRANDS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
