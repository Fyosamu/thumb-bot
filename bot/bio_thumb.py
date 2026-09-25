# -*- coding: utf-8 -*-
"""Biography channel thumbnail: the subject's real portrait + gold title.

  top line    : زندگی‌نامه‌ی من        (Persian, exactly as requested)
  second line : MY LIFE STORY / the person's name (English)

Portrait source = Wikipedia (free, no key, no captcha). Pexels is the fallback.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gold_thumb import (GOLD_BOT, GOLD_MID, GOLD_TOP, IMPACT,  # noqa: E402
                        gold_gradient, load_font, wrap)

W, H = 1280, 720
TITLE_FA = "زندگی‌نامه‌ی من"
TITLE_EN = "MY LIFE STORY"


def _fa_font(size):
    for p in (r"C:\Windows\Fonts\tahomabd.ttf", r"C:\Windows\Fonts\tahoma.ttf",
              r"C:\Windows\Fonts\arialbd.ttf"):
        if os.path.exists(p):
            return ImageFont_truetype(p, size)
    raise RuntimeError("no persian-capable font")


def ImageFont_truetype(path, size):
    from PIL import ImageFont
    return ImageFont.truetype(path, size)


def shape_fa(text):
    """RTL shaping for Persian (arabic_reshaper + bidi)."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:                                  # noqa: BLE001
        return text


def face_crop(img, w, h, anchor=0.30):
    """Cover-crop keeping the upper part (portraits: keep the face)."""
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale + 0.5), int(ih * scale + 0.5)
    img = img.resize((nw, nh), Image.LANCZOS)
    x = max(0, (nw - w) // 2)
    y = max(0, int((nh - h) * anchor))
    return img.crop((x, y, x + w, y + h))


def _gold_lines(base, lines, y0, box_pad=(24, 12), accent=None):
    """Black boxes (no border) + gradient text, centred, glued to top.

    accent=None -> classic gold; accent=(r,g,b) -> colour of the glow frame.
    """
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    boxes = []
    yy = y0
    for text, font, maxw in lines:
        fnt = font
        while probe.textlength(text, font=fnt) > maxw and fnt.size > 26:
            fnt = ImageFont_truetype(fnt.path, fnt.size - 4)
        tl = probe.textlength(text, font=fnt)
        bw, bh = int(tl) + box_pad[0] * 2, fnt.size + box_pad[1] * 2
        boxes.append((text, fnt, (W - bw) // 2, yy, bw, bh))
        yy += bh + 10

    # shadow
    sh = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sh)
    for _, _, bx, by, bw, bh in boxes:
        sd.rounded_rectangle([bx + 6, by + 8, bx + bw + 6, by + bh + 8], radius=10, fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    base.paste((0, 0, 0), (0, 0), sh)

    d = ImageDraw.Draw(base)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    for text, fnt, bx, by, bw, bh in boxes:
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=(0, 0, 0))
        md.text((bx + box_pad[0], by + box_pad[1] - int(fnt.size * 0.14)),
                text, font=fnt, fill=255)
    if accent:
        from glow_frame import accent_gradient
        grad = accent_gradient(W, H, accent)
    else:
        grad = gold_gradient(W, H)
    base.paste(grad, (0, 0), mask)
    return yy, base


def make(photo_path, out, person_name=None, extra_line=None, anchor=0.28,
         accent=None, color_seed=None, fa=False):
    from glow_frame import add_glow, next_color

    img = Image.open(photo_path)
    from thumb_layout import build_canvas
    base = build_canvas(img.convert("RGB"), W, H, zone=(0.34, 0.97))

    if accent is None:
        accent = next_color()[1]

    lines = ([(shape_fa(TITLE_FA), _fa_font(74), W - 80)] if fa
             else [(TITLE_EN, load_font(78), W - 80)])
    if person_name:
        lines.append((person_name.upper(), load_font(44), W - 260))
    if extra_line:
        lines.append((extra_line.upper(), load_font(34), W - 320))
    _, base = _gold_lines(base, lines, y0=12, accent=accent)

    seed = color_seed if color_seed is not None else (hash(person_name or out) & 0xFFFF)
    base = add_glow(base, accent, strength=1.0, seed=seed)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    base.save(out, quality=95)
    return out


def make_subject(name, out, accent=None, source="pexels", lang="en", hook=None):
    """Thumbnail for a biography video.

    source="pexels"    -> free Pexels photo (requested default)
    source="portrait"  -> the person's real portrait from Wikipedia
    text on top        : زندگی‌نامه‌ی من  +  the person's name  + a related hook
    """
    from hooks_lib import build_life_hooks
    import photo_lib

    if source == "portrait":
        photo = os.path.join(os.path.dirname(out) or ".", "_src_%s.jpg"
                             % name.replace(" ", "_"))
        info = get_portrait(name, photo, lang=lang)
        person = info["title"]
    else:
        photo = photo_lib.get_photo("biography",
                                    os.path.join(HERE, "_tmp_bio.jpg"))
        person = name
    if hook is None:
        pool = build_life_hooks([name])
        hook = pool[abs(hash(name)) % len(pool)]
    make(photo, out, person_name=person, extra_line=hook, accent=accent)
    return out, person, hook


def make_for_subject(title, out_dir, lang="en", source="pexels"):
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "bio_%s.jpg" % title.replace(" ", "_"))
    p, person, hook = make_subject(title, out, source=source, lang=lang)
    return p, {"title": person, "hook": hook}


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\USER\Desktop\chess_sample"
    subject = sys.argv[2] if len(sys.argv) > 2 else "Nikola Tesla"
    src = sys.argv[3] if len(sys.argv) > 3 else "pexels"
    p, info = make_for_subject(subject, outdir, source=src)
    print("saved", p, "|", info["title"], "|", info["hook"])
