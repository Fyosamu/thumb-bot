# -*- coding: utf-8 -*-
"""Thumbnail layout: keep the WHOLE photo sharp and readable.

The photo is placed inside a reserved area (never cropped through the
subject), on a darkened blurred copy of itself. The text lives in the top
zone, so it never covers the subject.

    base = build_canvas(photo, W, H, zone=(0.30, 0.96))
"""

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

LANCZOS = Image.LANCZOS


def fit_cover(img, w, h):
    iw, ih = img.size
    s = max(w / iw, h / ih)
    nw, nh = int(iw * s + .5), int(ih * s + .5)
    img = img.resize((nw, nh), LANCZOS)
    return img.crop(((nw - w) // 2, (nh - h) // 2,
                     (nw - w) // 2 + w, (nh - h) // 2 + h))


def _rounded(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1],
                                        radius=radius, fill=255)
    return m


def build_canvas(img, w, h, zone=(0.30, 0.96), pad=0.035, blur=30, darken=0.42,
                 radius=18):
    """Blurred dark background + the full photo, sharp, inside `zone`."""
    img = img.convert("RGB")
    bg = fit_cover(img, w, h).filter(ImageFilter.GaussianBlur(blur))
    bg = ImageEnhance.Brightness(bg).enhance(darken)
    bg = ImageEnhance.Color(bg).enhance(0.7)

    x0, y0 = int(w * pad), int(h * zone[0])
    x1, y1 = int(w * (1 - pad)), int(h * zone[1])
    aw, ah = x1 - x0, y1 - y0

    iw, ih = img.size
    s = min(aw / iw, ah / ih)
    nw, nh = max(8, int(iw * s)), max(8, int(ih * s))
    if nw > aw:
        nh = int(nh * aw / nw)
        nw = aw
    if nh > ah:
        nw = int(nw * ah / nh)
        nh = ah
    inset = img.resize((nw, nh), LANCZOS)

    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    px, py = cx - nw // 2, cy - nh // 2

    # soft shadow so the photo separates from the background
    sh = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sh).rounded_rectangle([px + 8, py + 10, px + nw + 8, py + nh + 10],
                                         radius=radius, fill=190)
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    bg.paste((0, 0, 0), (0, 0), sh)

    mask = _rounded((nw, nh), radius)
    bg.paste(inset, (px, py), mask)

    # thin frame line around the photo
    d = ImageDraw.Draw(bg)
    d.rounded_rectangle([px, py, px + nw - 1, py + nh - 1], radius=radius,
                        outline=(24, 24, 26), width=3)
    return bg


if __name__ == "__main__":
    print("layout ok")
