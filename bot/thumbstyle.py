# -*- coding: utf-8 -*-
"""The ONE thumbnail style every channel uses now.

Reference: ffff\\yt_factory\\out\\age.jpg  (the thumbnail the owner picked)

  * photo, cover-fit, light 2px blur
  * a 50%-black band from 55% of the height down to the bottom
  * BOLD GOLD text, black drop shadow, centred, starting at 60% height
    -> i.e. the text sits in the TOP part of that dark band

Never crop through the subject, never paint text on the face, never use a
dark text colour.  Long = 16:9, short = 9:16.
"""
import os
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

GOLD = (255, 214, 10)          # exactly the reference colour
SHADOW = (0, 0, 0, 230)
BAND_TOP = 0.55                # dark band starts here
TEXT_TOP = 0.60                # first text line baseline area
BAND_ALPHA = 150               # ~50% black
BLUR = 2

LONG = (1280, 720)
SHORT = (720, 1280)

_FONTS = (r'C:\Windows\Fonts\arialbd.ttf',
          r'C:\Windows\Fonts\segoeuib.ttf',
          r'C:\Windows\Fonts\arial.ttf')


def _font(size):
    for p in _FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def fit_cover(img, w, h):
    """Fill w x h, centred, without changing the aspect ratio."""
    img = img.convert('RGB')
    scale = max(w / img.width, h / img.height)
    nw, nh = max(w, int(img.width * scale + 0.5)), max(h, int(img.height * scale + 0.5))
    img = img.resize((nw, nh), Image.LANCZOS)
    x, y = (nw - w) // 2, (nh - h) // 2
    return img.crop((x, y, x + w, y + h))


def _fit_font(draw, lines, size, max_w):
    """Start at `size` and shrink until the LONGEST line fits max_w."""
    lines = [ln for ln in lines if ln]
    s = size
    while s > 12:
        f = _font(s)
        if max((draw.textlength(ln, font=f) for ln in lines), default=0) <= max_w:
            return f, s
        s = int(s * 0.94)
    return _font(12), 12


def render(photo, text, mode='long', sub=None, dest=None, quality=93,
           box=None, blur=BLUR):
    """photo: path | PIL.Image.  text: str (\\n allowed).  sub: optional line.

    box: (x, y, w, h) region to fill (defaults to the whole canvas) - lets a
    portrait photo sit inside a 9:16 frame without cropping through the face.
    """
    w, h = LONG if mode == 'long' else SHORT
    if isinstance(photo, str):
        photo = Image.open(photo)
    if box is None:
        canvas = fit_cover(photo, w, h)
    else:
        bx, by, bw, bh = box
        cell = fit_cover(photo, bw, bh)
        canvas = Image.new('RGB', (w, h), (18, 18, 24))
        canvas.paste(cell, (bx, by))
    if blur:
        canvas = canvas.filter(ImageFilter.GaussianBlur(blur))

    d = ImageDraw.Draw(canvas, 'RGBA')

    # --- the 50% black band, bottom -> middle -------------------------------
    d.rectangle([0, int(h * BAND_TOP), w, h], fill=(0, 0, 0, BAND_ALPHA))

    # --- gold text ----------------------------------------------------------
    wrapw = 18 if mode == 'long' else 11
    lines = [ln for ln in text.upper().split('\n') if ln.strip()]
    wrapped = []
    for ln in lines:
        wrapped.extend(textwrap.wrap(ln, width=wrapw,
                                     break_long_words=False,
                                     break_on_hyphens=False) or [ln])
    if not wrapped:
        wrapped = ['']

    # size must fit the widest line AND the whole block inside the dark band
    size0 = int(h * (0.13 if len(' '.join(wrapped)) < 34 else 0.105))
    avail_h = h * 0.97 - h * TEXT_TOP
    sub_lines = [sub.upper()] if sub else []
    font, size = _font(size0), size0
    while size > 14:
        font, size = _fit_font(d, wrapped, size, w * 0.92)
        need = (len(wrapped) + len(sub_lines)) * size * 1.12
        if need <= avail_h:
            break
        size = int(size * 0.94)
        font, size = _fit_font(d, wrapped, size, w * 0.92)
    font, size = _fit_font(d, wrapped, size, w * 0.92)

    y = int(h * TEXT_TOP)
    for line in wrapped:
        lw = d.textlength(line, font=font)
        x = (w - lw) / 2
        d.text((x + 4, y + 4), line, font=font, fill=SHADOW)
        d.text((x, y), line, font=font, fill=GOLD + (255,))
        y += int(size * 1.12)

    if sub:
        stext = sub.upper()
        sfont, ssize = _fit_font(d, [stext], int(size * 0.52), w * 0.86)
        slw = d.textlength(stext, font=sfont)
        sx = (w - slw) / 2
        d.text((sx + 3, y + 3), stext, font=sfont, fill=SHADOW)
        d.text((sx, y), stext, font=sfont, fill=GOLD + (255,))
        y += int(ssize * 1.15)

    # keep the block inside the dark band
    canvas.save(dest, 'JPEG', quality=quality) if dest else None
    return canvas


def make(src_photo, text, dest, mode='long', sub=None, **kw):
    im = render(src_photo, text, mode=mode, sub=sub, **kw)
    if dest:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        im.save(dest, 'JPEG', quality=93)
    return dest
