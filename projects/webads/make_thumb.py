# -*- coding: utf-8 -*-
"""Custom thumbnails for the web-design ad bank.

    python make_thumb.py <script.json> <out.jpg>

Reads the script (thumb_text / title / template) and overwrites the jpg
factory.py generated, in the Pinterest-grade style of pinterest-brief.md:
indigo->violet gradient, browser mockup card, lime accent, price badge.
Auto-shrinks every text block against WIDTH (never height) until it fits.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
INDIGO = (27, 31, 92)
VIOLET = (91, 43, 217)
LIME = (198, 255, 61)
WHITE = (255, 255, 255)
NEAR_BLACK = (14, 16, 32)
GREY = (222, 224, 232)
CARD = (250, 250, 252)


def _font_path(bold: bool) -> str:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return ""


def _load(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    p = _font_path(bold)
    if p:
        return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _fit(text: str, max_w: int, start: int, bold: bool = True,
         max_lines: int = 3) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Shrink font and wrap so every line is <= max_w, <= max_lines."""
    size = start
    while size > 40:
        f = _load(size, bold)
        words, lines, cur = text.split(), [], ""
        ok = True
        for w in words:
            trial = (cur + " " + w).strip()
            if f.getlength(trial) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
                if f.getlength(w) > max_w or len(lines) >= max_lines:
                    ok = False
                    break
        if cur and len(lines) < max_lines:
            lines.append(cur)
        if ok and cur and len(lines) <= max_lines:
            return f, lines
        size -= 6
    return _load(40, bold), [text[:30]]


def _gradient() -> Image.Image:
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(
            int(INDIGO[i] + (VIOLET[i] - INDIGO[i]) * t) for i in range(3)))
    # subtle dot grid
    dot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dot)
    for y in range(60, H, 90):
        for x in range(60, W, 90):
            dd.ellipse([x, y, x + 5, y + 5], fill=(255, 255, 255, 18))
    return Image.alpha_composite(img.convert("RGBA"), dot).convert("RGB")


def _browser_card(img: Image.Image, box: tuple[int, int, int, int]) -> None:
    """Browser mockup that adapts to ANY card height: header always, body
    lines when they fit, CTA when they fit, columns only when they fit."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=28, fill=CARD, outline=(210, 212, 224), width=3)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([x0 + 26 + i * 42, y0 + 24, x0 + 52 + i * 42, y0 + 50], fill=c)
    d.rounded_rectangle([x0 + 180, y0 + 20, x1 - 26, y0 + 56], radius=18, fill=GREY)
    f = _load(24, False)
    d.text((x0 + 200, y0 + 26), "yourbusiness.com", font=f, fill=(110, 112, 128))

    pad = 30
    cx0, cx1 = x0 + pad, x1 - pad
    cy0 = y0 + 86
    content_h = (y1 - pad) - cy0
    if content_h < 70:
        return
    cw = cx1 - cx0
    d.rounded_rectangle([cx0, cy0, cx1, cy0 + 56], radius=12, fill=VIOLET)
    if content_h < 120:
        return
    d.rectangle([cx0, cy0 + 76, cx0 + int(cw * 0.62), cy0 + 100], fill=(60, 62, 90))
    if content_h < 150:
        return
    d.rectangle([cx0, cy0 + 116, cx0 + int(cw * 0.45), cy0 + 136], fill=(60, 62, 90))
    if content_h >= 330:
        d.rounded_rectangle([cx0, cy0 + 168, cx0 + 210, cy0 + 218], radius=12,
                            fill=LIME)
        col_y = (y1 - pad) - 130
        col_w = (cw - 2 * 20) // 3
        for i in range(3):
            x = cx0 + i * (col_w + 20)
            d.rounded_rectangle([x, col_y, x + col_w, col_y + 130], radius=14,
                                outline=(205, 207, 220), width=3)
            d.rectangle([x + 18, col_y + 24, x + col_w - 18, col_y + 44], fill=GREY)
            d.rectangle([x + 18, col_y + 60, x + col_w - 40, col_y + 76], fill=GREY)


def _badge(img: Image.Image, cx: int, cy: int, r: int, line1: str, line2: str) -> None:
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=LIME)
    f1 = _load(58)
    f2 = _load(40)
    d.text((cx, cy - 24), line1, font=f1, fill=NEAR_BLACK, anchor="mm")
    d.text((cx, cy + 34), line2, font=f2, fill=NEAR_BLACK, anchor="mm")


def _strip(img: Image.Image, text: str) -> None:
    d = ImageDraw.Draw(img)
    f = _load(44)
    d.rectangle([0, H - 150, W, H], fill=(12, 12, 28))
    d.text((W // 2, H - 75), text, font=f, fill=WHITE, anchor="mm")


def render(script: dict, out: Path) -> None:
    img = _gradient()
    d = ImageDraw.Draw(img)
    tpl = script.get("template", "mockup")
    head = script.get("thumb_text") or script.get("topic", "WEB DESIGN")
    headline = head.upper()

    if tpl == "question":
        f, lines = _fit(headline + "?", W - 160, 118)
        y = 300
        for ln in lines:
            d.text((W // 2, y), ln, font=f, fill=WHITE, anchor="mm")
            y += f.size + 24
        _browser_card(img, (110, y + 120, W - 110, 1330))
    elif tpl == "price":
        f, lines = _fit(headline, W - 200, 104)
        y = 340
        for ln in lines:
            d.text((W // 2, y), ln, font=f, fill=WHITE, anchor="mm")
            y += f.size + 22
        _badge(img, W // 2, y + 260, 220, "FROM", "$1,000")
        _browser_card(img, (150, y + 540, W - 150, 1620))
    elif tpl == "stat":
        f_big = _load(300)
        d.text((W // 2, 520), "-7%", font=f_big, fill=LIME, anchor="mm")
        f, lines = _fit("EVERY SECOND OF LOAD TIME COSTS SALES",
                        W - 200, 72)
        y = 800
        for ln in lines:
            d.text((W // 2, y), ln, font=f, fill=WHITE, anchor="mm")
            y += f.size + 18
        _browser_card(img, (150, y + 60, W - 150, 1620))
    elif tpl == "checklist":
        card = (110, 300, W - 110, 1330)
        d.rounded_rectangle(card, radius=28, fill=CARD)
        f = _load(64)
        d.text((W // 2, 380), "YOUR SITE GETS", font=f, fill=NEAR_BLACK, anchor="mm")
        f2 = _load(58)
        items = ["SEO from day one", "Loads under 2 s", "Mobile-first",
                 "Secure + backed up", "30 days support"]
        y = 500
        for it in items:
            d.ellipse([170, y - 26, 222, y + 26], fill=LIME)
            d.line([(182, y), (196, y + 16), (212, y - 16)], fill=NEAR_BLACK,
                   width=8, joint="curve")
            d.text((250, y), it, font=f2, fill=NEAR_BLACK, anchor="lm")
            y += 150
    elif tpl == "beforeafter":
        d.polygon([(0, 0), (W, 0), (W, H), (0, H)], fill=INDIGO)
        d.polygon([(W // 2, 0), (W, 0), (W, H), (W // 2 + 140, H)], fill=VIOLET)
        d.line([(W // 2 - 40, H), (W // 2 + 120, 0)], fill=LIME, width=10)
        f = _load(52)
        d.text((W * 0.25, 260), "BEFORE", font=f, fill=(150, 150, 175), anchor="mm")
        d.text((W * 0.75, 260), "AFTER", font=f, fill=LIME, anchor="mm")
        _browser_card(img, (70, 380, W // 2 - 90, 1180))
        d.rounded_rectangle((W // 2 + 60, 380, W - 70, 1180), radius=28,
                            fill=CARD, outline=LIME, width=6)
        _browser_card(img, (W // 2 + 70, 390, W - 80, 1170))
        f2, lines = _fit(headline, W - 180, 86)
        y = 1330
        for ln in lines:
            d.text((W // 2, y), ln, font=f2, fill=WHITE, anchor="mm")
            y += f2.size + 20
    else:  # mockup
        f, lines = _fit(headline, W - 160, 108)
        y = 300
        for ln in lines:
            d.text((W // 2, y), ln, font=f, fill=WHITE, anchor="mm")
            y += f.size + 24
        _browser_card(img, (110, y + 110, W - 110, 1360))
        _badge(img, W - 260, 1500, 190, "FROM", "$1,000")

    _strip(img, "FULL SEO  *  MOBILE-FIRST  *  FROM $1,000")
    img.save(out, "JPEG", quality=88)
    print(f"thumb: {out}")


def main(argv) -> int:
    script = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    render(script, Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
