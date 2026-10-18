# -*- coding: utf-8 -*-
"""Ten thumbnail styles for the chess channel - visual lab.

Renders the same real episode board ten ways so the styles can be
compared side by side, writes the full-size samples plus a contact
sheet.  Effects live at the frame edges (fire auras, neon, plasma...)
so the board and the dare text stay readable in the middle.

    python _thumb_lab.py            # 10 landscape samples + contact sheet
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chess_factory as cf                      # noqa: E402
from board_renderer import render_board         # noqa: E402

import json                                     # noqa: E402
from PIL import (Image, ImageChops, ImageDraw, ImageFilter,    # noqa: E402
                 ImageFont, ImageOps)

CONTENT = HERE / "content_chess"
SAMPLES = Path.home() / "Desktop" / "خخخکککخ" / "شطرنج_تامنیل"
GOLD = (255, 214, 10)
FONT = next((fp for fp in (r"C:\Windows\Fonts\arialbd.ttf",
                           r"C:\Windows\Fonts\arial.ttf")
             if Path(fp).exists()), None)


def base(script: dict, pz: dict, part: int, pre=None) -> Image.Image:
    """The house layout: board left, band from 55%, gold dare, PART."""
    w, h = 1920, 1080
    canvas = Image.new("RGB", (w, h), (30, 31, 33))
    if pre is not None:
        pre(canvas)                       # backdrop rays go BEHIND the board
    side = int(h * 0.96)
    board = render_board(pz["fen"], size=side).convert("RGB")
    canvas.paste(board, (int(w * 0.035), (h - side) // 2))

    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle([0, int(h * 0.55), w, h], fill=(0, 0, 0, 178))

    text = cf.hook_text(script)
    fsize = int(h * 0.085)
    font = ImageFont.truetype(FONT, fsize)
    lines = __import__("textwrap").wrap(text, width=22)[:3]
    while max(draw.textlength(l, font=font) for l in lines) > w * 0.9:
        fsize = int(fsize * 0.9)
        font = ImageFont.truetype(FONT, fsize)
    y = int(h * 0.60)
    for line in lines:
        lw = draw.textlength(line, font=font)
        x = (w - lw) / 2
        draw.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0, 230))
        draw.text((x, y), line, font=font, fill=GOLD + (255,))
        y += int(fsize * 1.12)

    if part:
        m, psize = int(min(w, h) * 0.030), int(min(w, h) * 0.055)
        pfont = ImageFont.truetype(FONT, psize)
        label, pad_x, pad_y = f"PART {part}", psize // 2, psize // 3
        bx2, by1 = w - m, m
        bx1 = bx2 - draw.textlength(label, font=pfont) - pad_x * 2
        by2 = m + psize + pad_y * 2
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=(by2 - by1) // 3,
                               fill=GOLD + (255,))
        draw.text((bx1 + pad_x, by1 + pad_y), label, font=pfont,
                  fill=(8, 8, 12, 255))
    return canvas


def edge_mask(w: int, h: int, thick: int, blur: int,
              bottom_only: bool = False) -> Image.Image:
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    steps = 12
    for i in range(steps):
        inset = int(thick * i / steps)
        val = int(255 * (1 - i / steps))
        d.rectangle([inset, inset, w - inset, h - inset], fill=val)
    d.rectangle([thick, thick, w - thick, h - thick], fill=0)  # true core
    if bottom_only:
        keep = Image.new("L", (w, h), 0)
        ImageDraw.Draw(keep).rectangle([0, int(h * 0.45), w, h], fill=255)
        mask = ImageChops.multiply(mask, keep)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def fire_ring(img: Image.Image, cold, warm, hot, thick: int = 170,
              blur: int = 55) -> Image.Image:
    """Wide glow + a searing line right at the edge: two masks, screen
    blended - this is what makes the border actually look hot."""
    img.paste(color_aura(img, edge_mask(*img.size, thick, blur),
                         cold, hot, warm))
    img.paste(color_aura(img, edge_mask(*img.size, 26, 9), cold, hot, hot))
    return img


def color_aura(img: Image.Image, mask: Image.Image, cold, hot, warm=None,
               alpha: float = 1.0) -> Image.Image:
    glow = ImageOps.colorize(mask, cold, hot, mid=warm)
    if alpha < 1.0:
        glow = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), glow, alpha)
    return ImageChops.screen(img, glow)


def sparks(img: Image.Image, n: int, palette, near: str = "edges") -> None:
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    for _ in range(n):
        if near == "edges":
            side = random.randrange(4)
            if side < 2:
                x = random.randrange(w)
                y = random.randrange(0, h // 5) if side == 0 \
                    else random.randrange(h * 4 // 5, h)
            else:
                x = random.randrange(0, w // 6) if side == 2 \
                    else random.randrange(w * 5 // 6, w)
                y = random.randrange(h)
        else:
            x, y = random.randrange(w), random.randrange(h)
        r = random.randrange(2, 7)
        c = random.choice(palette)
        d.ellipse([x - r, y - r, x + r, y + r], fill=c + (random.randrange(120, 255),))


SCRIPT: dict | None = None


def glow_text(img: Image.Image, _script, color, offset: int = 10,
              passes: int = 3) -> None:
    """Re-draw the dare text with a colored halo on top of the base."""
    w, h = img.size
    import textwrap
    text = cf.hook_text(SCRIPT)
    fsize = int(h * 0.085)
    font = ImageFont.truetype(FONT, fsize)
    lines = textwrap.wrap(text, width=22)[:3]
    probe = ImageDraw.Draw(img)
    while max(probe.textlength(l, font=font) for l in lines) > w * 0.9:
        fsize = int(fsize * 0.9)
        font = ImageFont.truetype(FONT, fsize)
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    y = int(h * 0.60)
    for line in lines:
        lw = probe.textlength(line, font=font)
        x = (w - lw) / 2
        for p in range(passes):
            a = 90 - p * 25
            for dx, dy in ((-offset, 0), (offset, 0), (0, -offset), (0, offset),
                           (-offset // 2, -offset // 2), (offset // 2, offset // 2)):
                hd.text((x + dx, y + dy), line, font=font, fill=color + (a,))
        y += int(fsize * 1.12)
    halo = halo.filter(ImageFilter.GaussianBlur(offset / 2))
    img.paste(Image.alpha_composite(img.convert("RGBA"), halo).convert("RGB"))
    d = ImageDraw.Draw(img)
    y = int(h * 0.60)
    for line in lines:
        lw = d.textlength(line, font=font)
        d.text(((w - lw) / 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += int(fsize * 1.12)


def sunburst(img: Image.Image) -> None:
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = int(w * 0.30), int(h * 0.45)
    r = int((w ** 2 + h ** 2) ** 0.5)
    for i in range(0, 360, 14):
        if i % 28:
            continue
        a0 = i * 3.14159 / 180
        a1 = (i + 7) * 3.14159 / 180
        d.polygon([cx, cy,
                   cx + r * __import__("math").cos(a0), cy + r * __import__("math").sin(a0),
                   cx + r * __import__("math").cos(a1), cy + r * __import__("math").sin(a1)],
                  fill=140)
    mask = mask.rotate(7, resample=Image.BILINEAR).filter(
        ImageFilter.GaussianBlur(6))
    img.paste(color_aura(img, mask, (0, 0, 0), (255, 196, 80),
                         (150, 40, 5)))


def lightning_edges(img: Image.Image) -> None:
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(7):
        side = random.randrange(4)
        pts = []
        n = 9
        for i in range(n):
            t = i / (n - 1)
            if side < 2:
                x = int(w * t)
                y = random.randrange(0, 26) if side == 0 else h - random.randrange(0, 26)
            else:
                x = random.randrange(0, 26) if side == 2 else w - random.randrange(0, 26)
                y = int(h * t)
            pts.append((x + random.randrange(-8, 8), y + random.randrange(-8, 8)))
        d.line(pts, fill=(140, 210, 255, 235), width=3)
        d.line(pts, fill=(255, 255, 255, 255), width=1)
    glow = layer.filter(ImageFilter.GaussianBlur(7))
    img.paste(ImageChops.screen(img, glow.convert("RGB")), (0, 0))
    img.paste(layer, (0, 0), layer)


def holo_frame(img: Image.Image) -> None:
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(0, h, 5):                      # scanlines
        d.rectangle([0, y, w, y + 1], fill=(0, 220, 255, 14))
    d.rectangle([6, 6, w - 6, h - 6], outline=(0, 230, 255, 200), width=3)
    b, L = 46, 90                                 # corner brackets
    for cx, cy, sx, sy in ((6, 6, 1, 1), (w - 6, 6, -1, 1),
                           (6, h - 6, 1, -1), (w - 6, h - 6, -1, -1)):
        d.line([cx, cy, cx + sx * L, cy], fill=(0, 255, 255, 255), width=8)
        d.line([cx, cy, cx, cy + sy * L], fill=(0, 255, 255, 255), width=8)
    d.rectangle([14, 14, w - 14, h - 14], outline=(0, 160, 255, 120), width=1)


def gold_frame(img: Image.Image) -> None:
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([10, 10, w - 10, h - 10], outline=(212, 175, 55, 255), width=7)
    d.rectangle([24, 24, w - 24, h - 24], outline=(255, 224, 120, 180), width=2)
    for cx, cy in ((10, 10), (w - 10, 10), (10, h - 10), (w - 10, h - 10)):
        d.polygon([(cx, cy - 22), (cx + 22, cy), (cx, cy + 22), (cx - 22, cy)],
                  fill=(212, 175, 55, 255))


def fire_edges_only(img: Image.Image) -> None:
    """Normal house colors everywhere - only a fire rim on the frame:
    a searing hairline at the very edge plus a short inward glow with
    cubic falloff, so the board sitting at the 3.5% margin stays its
    own color and the gold dare text is untouched."""
    w, h = img.size
    glow = edge_mask(w, h, 90, 14)
    glow = ImageChops.multiply(ImageChops.multiply(glow, glow), glow)
    # cold = pure black: outside the rim the screen-blend must be a
    # no-op, or the whole canvas picks up a warm cast
    img.paste(color_aura(img, glow, (0, 0, 0), (255, 226, 130),
                         (255, 92, 10)))
    img.paste(color_aura(img, edge_mask(w, h, 9, 3), (0, 0, 0),
                         (255, 250, 200), (255, 150, 30)))
    sparks(img, 30, [(255, 150, 30), (255, 225, 95), (255, 90, 12)])


def corner_mask(w: int, h: int, r_frac: float = 0.45) -> Image.Image:
    """Four soft blobs hugging the corners, near-nothing in the middle:
    the inverted radial gradient is centered ON each corner (half of it
    falls off-canvas), so the color lives where the eye enters the frame
    and the center stays under ~12% tinted."""
    r = int(w * r_frac)
    # brightest at the gradient's own center, zero at distance r: crop the
    # quarter whose hot core lands exactly on the canvas corner
    g = ImageOps.invert(Image.radial_gradient("L")
                        .resize((2 * r, 2 * r), Image.BILINEAR))
    g = g.crop((r, r, 2 * r, 2 * r))
    g = ImageChops.multiply(ImageChops.multiply(g, g), g)   # cubic falloff
    g = g.filter(ImageFilter.GaussianBlur(r // 12))
    mask = Image.new("L", (w, h), 0)
    mask.paste(g, (0, 0))
    mask.paste(ImageOps.mirror(g), (w - r, 0))
    mask.paste(ImageOps.flip(g), (0, h - r))
    mask.paste(ImageOps.mirror(ImageOps.flip(g)), (w - r, h - r))
    return mask


def corner_glow(img: Image.Image, cold, warm, hot) -> None:
    w, h = img.size
    img.paste(color_aura(img, corner_mask(w, h), cold, hot, warm))
    # a whisper-thin rim keeps the frame shape readable
    img.paste(color_aura(img, edge_mask(w, h, 18, 7), cold, warm, hot))
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(26):                      # sparks live in the corners
        corner = random.randrange(4)
        if corner == 0:
            x, y = random.randrange(w // 3), random.randrange(h // 3)
        elif corner == 1:
            x, y = w - random.randrange(w // 3), random.randrange(h // 3)
        elif corner == 2:
            x, y = random.randrange(w // 3), h - random.randrange(h // 3)
        else:
            x, y = w - random.randrange(w // 3), h - random.randrange(h // 3)
        rr = random.randrange(2, 6)
        c = random.choice([(225, 135, 255), (255, 195, 255), (170, 90, 255)])
        d.ellipse([x - rr, y - rr, x + rr, y + rr],
                  fill=c + (random.randrange(120, 230),))


STYLES = {
    "01_fire_ember": lambda img: (
        sparks(img, 44, [(255, 150, 30), (255, 225, 95), (255, 80, 10)]),
        fire_ring(img, (50, 4, 0), (255, 96, 12), (255, 240, 160), 170, 55)),
    "02_molten_ring": lambda img: (
        fire_ring(img, (30, 0, 0), (235, 60, 5), (255, 215, 95), 260, 90),
        sparks(img, 80, [(255, 200, 60), (255, 110, 20), (255, 245, 180)])),
    "03_neon_versus": lambda img: (
        fire_ring(img, (0, 10, 40), (255, 40, 130), (70, 245, 255), 150, 48),
        glow_text(img, None, (0, 230, 255))),
    "04_plasma_corners": lambda img: (
        corner_glow(img, (0, 0, 0), (170, 40, 255), (255, 170, 255)),
        glow_text(img, None, (205, 125, 255), 8, 2)),
    "05_toxic_rim": lambda img: (
        fire_ring(img, (0, 16, 0), (45, 215, 35), (200, 255, 70), 150, 46),
        glow_text(img, None, (175, 255, 65))),
    "06_gold_royal": lambda img: (gold_frame(img),),
    "07_inferno_rise": lambda img: (
        color_aura(img, edge_mask(*img.size, 320, 80, bottom_only=True),
                   (14, 0, 0), (255, 240, 150), (255, 105, 15)),
        color_aura(img, edge_mask(*img.size, 60, 18, bottom_only=True),
                   (20, 0, 0), (255, 250, 190), (255, 140, 25)),
        sparks(img, 60, [(255, 170, 40), (255, 240, 160)])),
    "08_storm_arc": lambda img: (lightning_edges(img),),
    "09_sunburst": "pre_sunburst",
    "10_holo_tech": lambda img: (holo_frame(img),
                                 glow_text(img, None, (0, 220, 255), 6, 2)),
    "11_fire_only": lambda img: (fire_edges_only(img),),
}


def main() -> int:
    global SCRIPT
    random.seed(67)
    script = json.loads((CONTENT / "chess_part0001.json")
                        .read_text(encoding="utf-8"))
    SCRIPT = script
    pz = script["puzzles"][0]
    SAMPLES.mkdir(parents=True, exist_ok=True)
    made = []
    for name, effect in STYLES.items():
        if effect == "pre_sunburst":
            img = base(script, pz, 1, pre=sunburst)
        else:
            img = base(script, pz, 1)
            for step in effect(img):
                pass
        dest = SAMPLES / f"{name}.jpg"
        img.save(dest, quality=92)
        made.append(img)
        print(f"{name} ok", flush=True)

    tw, th = 720, 405                              # contact sheet
    rows = (len(made) + 1) // 2
    sheet = Image.new("RGB", (tw * 2 + 30, (th + 46) * rows + 10),
                      (12, 12, 16))
    d = ImageDraw.Draw(sheet)
    lab = ImageFont.truetype(FONT, 26)
    for i, (img, name) in enumerate(zip(made, STYLES)):
        col, row = i % 2, i // 2
        x, y = 10 + col * (tw + 10), 10 + row * (th + 46)
        sheet.paste(img.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 8, y + th + 6), f"{i + 1}. {name[3:]}", font=lab,
               fill=(255, 214, 10))
    sheet.save(SAMPLES / "_contact_sheet.jpg", quality=90)
    print(f"\n{len(made)} styles + contact sheet -> {SAMPLES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
