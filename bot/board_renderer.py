# -*- coding: utf-8 -*-
"""Lichess-exact board renderer (official cburnett pieces, brown theme)."""
import os, math
from PIL import Image, ImageDraw, ImageFont

PIECE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "pieces")
# the Windows box has Georgia and Segoe; the Linux runner swaps DejaVu
_LIN = {"georgia.ttf": "DejaVuSerif-Bold.ttf",
        "segoeuib.ttf": "DejaVuSans-Bold.ttf",
        "segoeui.ttf": "DejaVuSans.ttf"}


def _fp(name):
    win = "C:/Windows/Fonts/" + name
    if os.path.exists(win):
        return win
    lin = os.path.join("/usr/share/fonts/truetype/dejavu", _LIN[name])
    return lin if os.path.exists(lin) else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
LIGHT = (240, 217, 181)   # lichess brown light  #f0d9b5
DARK  = (181, 136, 99)    # lichess brown dark   #b58863
HLMASK = (255, 213, 79, 96)
ARROW  = (155, 199, 0, 128)

def parse_fen(fen):
    board = {}
    for r, row in enumerate(fen.split()[0].split("/")):
        c = 0
        for ch in row:
            if ch.isdigit(): c += int(ch)
            else:
                board[(c, 7-r)] = ch; c += 1
    return board

def piece_img(p, S):
    im = Image.open(os.path.join(PIECE_DIR, ("w" if p.isupper() else "b") + p.upper() + ".png")).convert("RGBA")
    return im.resize((S, S), Image.LANCZOS)

def sq_xy(sq, S, ox, oy):
    f = ord(sq[0]) - 97; r = int(sq[1]) - 1
    return ox + f*S, oy + (7-r)*S

def draw_arrow(layer, a, b, S, ox, oy):
    d = ImageDraw.Draw(layer)
    x1,y1 = sq_xy(a,S,ox,oy); x2,y2 = sq_xy(b,S,ox,oy)
    cx, cy = x1+S/2, y1+S/2; dx, dy = x2+S/2, y2+S/2
    ang = math.atan2(dy-cy, dx-cx)
    w = S*0.22
    sx, sy = cx + S*0.18*math.cos(ang), cy + S*0.18*math.sin(ang)
    ex, ey = dx - w*0.75*math.cos(ang), dy - w*0.75*math.sin(ang)
    d.line([sx,sy,ex,ey], fill=ARROW, width=int(w))
    hw = w*1.4
    for s in (-1, 1):
        d.polygon([(ex,ey),
                   (ex + hw*math.cos(ang + s*0.42), ey + hw*math.sin(ang + s*0.42)),
                   (ex + hw*0.4*math.cos(ang), ey + hw*0.4*math.sin(ang))], fill=ARROW)

def render_board(fen, size=1440, title=None, top2=None, foot=None, foot2=None,
                 last=None, sol=None, gold=False):
    S = size // 8
    pad_top = int(size*0.22) if title else int(size*0.06)
    pad_bot = int(size*0.22) if foot else int(size*0.06)
    pad = int(size*0.05)
    W = size + 2*pad
    H = size + pad_top + pad_bot
    oy = pad_top; ox = pad
    img = Image.new("RGBA", (W, H), (36, 37, 38, 255))
    board = parse_fen(fen)
    for r in range(8):
        for c in range(8):
            x, y = ox + c*S, oy + (7-r)*S
            img.paste(Image.new("RGBA",(S,S), LIGHT if (c+r)%2==0 else DARK), (x,y))
    if last:
        hl = Image.new("RGBA", (W, H), (0,0,0,0)); hd = ImageDraw.Draw(hl)
        for sq in last:
            x, y = sq_xy(sq, S, ox, oy)
            hd.rectangle([x, y, x+S, y+S], fill=HLMASK)
        img = Image.alpha_composite(img, hl)
    if sol and len(sol) == 2:
        al = Image.new("RGBA", (W, H), (0,0,0,0))
        draw_arrow(al, sol[0], sol[1], S, ox, oy)
        img = Image.alpha_composite(img, al)
    for (c, r), p in board.items():
        x, y = ox + c*S, oy + (7-r)*S
        img.alpha_composite(piece_img(p, S), (x, y))
    d = ImageDraw.Draw(img)
    fs = max(18, int(S*0.20))
    fnt = ImageFont.truetype(_fp("georgia.ttf"), fs)
    for i in range(8):
        x, y = ox + i*S, oy + 7*S
        d.text((x + S - fs*0.35, y + S - fs*0.35), chr(97+i), font=fnt,
               anchor="rs", fill=LIGHT if i % 2 == 1 else DARK)
        x, y = ox, oy + (7-i)*S
        d.text((x + fs*0.35, y + fs*0.3), str(i+1), font=fnt,
               anchor="ls", fill=LIGHT if i % 2 == 0 else DARK)
    if title:
        tf = ImageFont.truetype(_fp("segoeuib.ttf"), int(size*0.085))
        if gold:
            metal_text(img, title, tf, (W//2, int(pad_top*0.10)), anchor="ma")
        else:
            d.text((W//2, int(pad_top*0.10)), title, font=tf, anchor="ma", fill=(255,255,255))
    if top2:
        tf2 = ImageFont.truetype(_fp("segoeui.ttf"), int(size*0.052))
        if gold:
            metal_text(img, top2, tf2, (W//2, int(pad_top*0.52)), anchor="ma",
                       stroke=max(2, int(size*0.010)))
        else:
            d.text((W//2, int(pad_top*0.52)), top2, font=tf2, anchor="ma", fill=(255, 196, 0))
    if foot:
        ff = ImageFont.truetype(_fp("segoeuib.ttf"), int(size*0.052))
        if gold:
            metal_text(img, foot, ff, (W//2, H - int(pad_bot*0.66)), anchor="ms")
        else:
            d.text((W//2, H - int(pad_bot*0.66)), foot, font=ff, anchor="ms", fill=(255,255,255))
    if foot2:
        ff2 = ImageFont.truetype(_fp("segoeui.ttf"), int(size*0.042))
        d.text((W//2, H - int(pad_bot*0.20)), foot2, font=ff2, anchor="ms", fill=(170, 170, 170))
    return img.convert("RGB")


# =========================================================================== #
#  16:9 layout for the LONG video:  board on the LEFT, text on the RIGHT.
#  The board is a square that fits the whole frame height -> never cut.
#  It NEVER draws the solution arrow or the last-move highlight, so the answer
#  is never revealed on screen.
# =========================================================================== #

GOLD = ((255, 244, 178), (255, 205, 74), (196, 130, 8))   # the font colour the
                                                          # user picked

def _metal(w, h, stops=GOLD):
    """3-stop polished-gold vertical gradient (light top -> gold -> deep)."""
    top, mid, bot = stops
    g = Image.new("RGB", (1, max(1, h)))
    px = g.load()
    for y in range(max(1, h)):
        t = y / max(1, h - 1)
        if t < 0.5:
            k = t / 0.5
            c = tuple(int(top[i] + (mid[i] - top[i]) * k) for i in range(3))
        else:
            k = (t - 0.5) / 0.5
            c = tuple(int(mid[i] + (bot[i] - mid[i]) * k) for i in range(3))
        px[0, y] = c
    return g.resize((max(1, w), max(1, h)))


def metal_text(img, text, font, xy, anchor="la", stroke=4, stops=GOLD):
    """Gold metallic text with a dark outline, drawn exactly like d.text()."""
    d = ImageDraw.Draw(img)
    d.text(xy, text, font=font, anchor=anchor, fill=(0, 0, 0),
           stroke_width=stroke, stroke_fill=(12, 11, 9))
    x0, y0, x1, y1 = d.textbbox(xy, text, font=font, anchor=anchor,
                                stroke_width=stroke)
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    tw, th = max(1, x1 - x0), max(1, y1 - y0)
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).text(xy, text, font=font, anchor=anchor, fill=255)
    img.paste(_metal(tw, th, stops), (x0, y0), m.crop((x0, y0, x1, y1)))
    return img


def _fit_font(draw, text, max_w, start, bold=True, floor=20):
    path = _fp("segoeuib.ttf" if bold else "segoeui.ttf")
    size = int(start)
    while size > floor:
        f = ImageFont.truetype(path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(path, floor)


def _wrap_txt(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def _paint_board(img, fen, S, ox, oy, last=None, sol=None):
    """Squares + pieces (+ optional highlight / solution arrow).

    For the puzzle video call it with last=None, sol=None -> NO answer shown.
    """
    board = parse_fen(fen)
    for r in range(8):
        for c in range(8):
            x, y = ox + c * S, oy + (7 - r) * S
            img.paste(Image.new("RGBA", (S, S),
                                LIGHT if (c + r) % 2 == 0 else DARK), (x, y))
    if last:
        hl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        hd = ImageDraw.Draw(hl)
        for sq in last:
            x, y = sq_xy(sq, S, ox, oy)
            hd.rectangle([x, y, x + S, y + S], fill=HLMASK)
        img.alpha_composite(hl)
    if sol and len(sol) == 2:
        al = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_arrow(al, sol[0], sol[1], S, ox, oy)
        img.alpha_composite(al)
    for (c, r), p in board.items():
        x, y = ox + c * S, oy + (7 - r) * S
        img.alpha_composite(piece_img(p, S), (x, y))
    d = ImageDraw.Draw(img)
    fs = max(18, int(S * 0.20))
    fnt = ImageFont.truetype(_fp("georgia.ttf"), fs)
    for i in range(8):
        x, y = ox + i * S, oy + 7 * S
        d.text((x + S - fs * 0.35, y + S - fs * 0.35), chr(97 + i), font=fnt,
               anchor="rs", fill=LIGHT if i % 2 == 1 else DARK)
        x, y = ox, oy + (7 - i) * S
        d.text((x + fs * 0.35, y + fs * 0.3), str(i + 1), font=fnt,
               anchor="ls", fill=LIGHT if i % 2 == 0 else DARK)


def render_frame_wide(fen, w=1920, h=1080, title=None, top2=None, foot=None,
                      foot2=None, reveal=False):
    """16:9 puzzle slide for the LONG video.

    * the board is a square that spans the FULL frame height (top edge to
      bottom edge) and sits a bit to the LEFT -> it covers that whole side
    * every line of text sits on the RIGHT of the board
    * reveal=False (default) -> the solution is never drawn
    * the main text uses the gold the user picked
    """
    S = h // 8                                     # full-height square
    size = S * 8
    ox = max(8, int(w * 0.010))                    # a bit to the left
    oy = (h - size) // 2

    canvas = Image.new("RGBA", (w, h), (36, 37, 38, 255))
    gh = int(h * 0.5)
    d = ImageDraw.Draw(canvas)
    for y in range(gh):
        a = 1 - y / gh
        d.line([(0, y), (w, y)], fill=(int(36 + 16 * a), int(37 + 12 * a),
                                       int(38 + 8 * a), 255))
    _paint_board(canvas, fen, S, ox, oy, last=None, sol=None)
    img = canvas.convert("RGB")
    d = ImageDraw.Draw(img)

    gap = int(w * 0.024)
    cl, cr = ox + size + gap, w - int(w * 0.030)
    cw = cr - cl
    cx = (cl + cr) // 2

    # the "White to play" line is styled EXACTLY like the title (bold gold)
    # and the gap between the two top lines is wider than it used to be.
    items = []                                      # (text, font, kind, after)
    if title:
        f = _fit_font(d, title, cw, h * 0.100, True, h * 0.048)
        items.append((title, f, "metal", int(h * 0.060)))
    if top2:
        f = _fit_font(d, top2, cw, h * 0.100, True, h * 0.048)
        items.append((top2, f, "metal", int(h * 0.075)))
    if foot:
        f = _fit_font(d, foot, cw, h * 0.060, True, h * 0.030)
        items.append((foot, f, "metal", int(h * 0.030)))
    if foot2:
        f = _fit_font(d, foot2, cw, h * 0.050, False, h * 0.030)
        items.append((foot2, f, "grey", 0))

    rows = []                                       # (line, font, kind, lh)
    for text, f, kind, after in items:
        lh = int(f.size * 1.28)
        lines = _wrap_txt(d, text, f, cw)
        for i, ln in enumerate(lines):
            rows.append((ln, f, kind, lh + (after if i == len(lines) - 1 else 0)))

    total = sum(r[3] for r in rows)
    y = (h - total) // 2
    for ln, f, kind, lh in rows:
        x = int(cx - d.textlength(ln, font=f) // 2)
        if kind == "metal":
            metal_text(img, ln, f, (x, y + int(lh * 0.06)))
        else:
            d.text((x, y + int(lh * 0.06)), ln, font=f, fill=(178, 178, 178))
        y += lh
    return img
