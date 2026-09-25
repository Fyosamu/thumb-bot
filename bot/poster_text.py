"""Colored glowing text on top of a generated background (poster / thumbnail).

    python bot/poster_text.py <bg.jpg> <out.jpg> "LINE1|color" "LINE2|color" ...

Colors: gold, cyan, pink, green, white, red  (or #RRGGBB)
Text is crisp and auto-shrunk to fit; every line gets a coloured halo plus a
dark drop shadow so it stays readable over any background.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

PALETTE = {
    "gold":   (255, 205, 74),
    "cyan":   (77, 225, 255),
    "pink":   (255, 95, 162),
    "green":  (60, 235, 140),
    "red":    (255, 88, 88),
    "white":  (250, 250, 250),
}

FONTS = [r"C:\Windows\Fonts\impact.ttf",
         r"C:\Windows\Fonts\arialbd.ttf",
         r"C:\Windows\Fonts\segoeuib.ttf"]


def font(size):
    for p in FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def color_of(name):
    if name.startswith("#"):
        return tuple(int(name[i:i + 2], 16) for i in (1, 3, 5))
    return PALETTE.get(name.lower(), PALETTE["gold"])


def fit(text, max_w, start):
    size = start
    f = font(size)
    while size > 24:
        w = ImageDraw.Draw(Image.new("RGB", (8, 8))).textbbox((0, 0), text, font=f)[2]
        if w <= max_w:
            break
        size -= 6
        f = font(size)
    return f


def _grad(w, h, top, mid, bot):
    """vertical 3-stop gradient, used as the metallic fill of the glyphs"""
    col = Image.new("RGB", (1, max(1, h)))
    px = []
    for i in range(max(1, h)):
        t = i / max(1, h - 1)
        if t < 0.5:
            k = t / 0.5
            c = tuple(int(top[j] + (mid[j] - top[j]) * k) for j in range(3))
        else:
            k = (t - 0.5) / 0.5
            c = tuple(int(mid[j] + (bot[j] - mid[j]) * k) for j in range(3))
        px.append(c)
    col.putdata(px)
    return col.resize((max(1, w), max(1, h)))


def glow_line(canvas, text, col, cy, max_w, h, metal=None, stroke=None):
    """draw one centred line: shadow -> wide halo -> tight halo -> outline ->
    crisp text.  metal=(top,mid,bot) fills the glyphs with that gradient
    (metallic gold) instead of the washed-out near-white core."""
    f = fit(text, max_w, int(h * 0.16))
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), text, font=f)
    x = (canvas.size[0] - (bb[2] - bb[0])) // 2 - bb[0]
    y = cy - (bb[3] - bb[1]) // 2 - bb[1]
    d.text((x, y), text, font=f, fill=col + (255,))

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((x + 5, y + 7), text, font=f, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    canvas.alpha_composite(shadow)

    halo = tmp.filter(ImageFilter.GaussianBlur(int(h * 0.05)))   # wide
    halo = Image.eval(halo, lambda v: min(255, int(v * 1.15)))
    canvas.alpha_composite(halo)
    halo2 = tmp.filter(ImageFilter.GaussianBlur(int(h * 0.016)))  # tight
    canvas.alpha_composite(halo2)

    if stroke is None:
        stroke = max(3, int((bb[3] - bb[1]) * 0.075))            # dark outline
    if stroke > 0:                                               # so it never blends in
        outl = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(outl).text((x, y), text, font=f, fill=(8, 6, 2, 255),
                                  stroke_width=stroke, stroke_fill=(8, 6, 2, 255))
        canvas.alpha_composite(outl)

    gw, gh = bb[2] - bb[0], bb[3] - bb[1]
    mask = Image.new("L", (gw, gh), 0)
    ImageDraw.Draw(mask).text((-bb[0], -bb[1]), text, font=f, fill=255)

    if metal:                                                    # gradient core
        fill = _grad(gw, gh, *metal)
    else:                                                        # near-white core
        fill = Image.new("RGB", (gw, gh),
                         tuple(min(255, int(c * 0.35 + 200)) for c in col))
    core = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
    core.paste(fill.convert("RGBA"), (0, 0), mask)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(core, (x + bb[0], y + bb[1]))
    canvas.alpha_composite(layer)


def build(bg, out, lines, anchor="bottom"):
    img = Image.open(bg).convert("RGB")
    W, H = img.size
    canvas = img.convert("RGBA")

    # soft dark veil where the text sits, so it always pops
    if anchor == "top":
        box, y0, y1 = (0, 0, W, int(H * 0.44)), 0.06, 0.40
    else:
        box, y0, y1 = (0, int(H * 0.30), W, H), 0.46, 0.96
    veil = Image.new("L", (W, H), 0)
    ImageDraw.Draw(veil).rectangle(box, fill=120)
    veil = veil.filter(ImageFilter.GaussianBlur(H * 0.12))
    canvas.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [veil]))

    n = len(lines)
    span = y1 - y0
    for i, (text, colname) in enumerate(lines):
        cy = int(H * (y0 + span * (i + 0.5) / n))
        glow_line(canvas, text, color_of(colname), cy, int(W * 0.9), H)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    canvas.convert("RGB").save(out, quality=95)
    print("saved %s | %s" % (out, " + ".join(t for t, _ in lines)))


if __name__ == "__main__":
    bg, out = sys.argv[1], sys.argv[2]
    specs = [s for s in sys.argv[3:] if not s.startswith("@")]
    anchor = "top" if any(s == "@top" for s in sys.argv[3:]) else "bottom"
    if anchor == "top" and not specs:
        specs = ["HE SACRIFICED HIS QUEEN|gold", "WATCH WHAT HAPPENS NEXT|cyan"]
    build(bg, out, [tuple(s.rsplit("|", 1)) for s in specs], anchor=anchor)
