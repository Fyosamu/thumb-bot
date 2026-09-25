# -*- coding: utf-8 -*-
"""Lichess-exact board renderer (official cburnett pieces, brown theme)."""
import os, math
from PIL import Image, ImageDraw, ImageFont

PIECE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "pieces")
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
                 last=None, sol=None):
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
    fnt = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", fs)
    for i in range(8):
        x, y = ox + i*S, oy + 7*S
        d.text((x + S - fs*0.35, y + S - fs*0.35), chr(97+i), font=fnt,
               anchor="rs", fill=LIGHT if i % 2 == 1 else DARK)
        x, y = ox, oy + (7-i)*S
        d.text((x + fs*0.35, y + fs*0.3), str(i+1), font=fnt,
               anchor="ls", fill=LIGHT if i % 2 == 0 else DARK)
    if title:
        tf = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", int(size*0.085))
        d.text((W//2, int(pad_top*0.10)), title, font=tf, anchor="ma", fill=(255,255,255))
    if top2:
        tf2 = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", int(size*0.052))
        d.text((W//2, int(pad_top*0.52)), top2, font=tf2, anchor="ma", fill=(255, 196, 0))
    if foot:
        ff = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", int(size*0.052))
        d.text((W//2, H - int(pad_bot*0.66)), foot, font=ff, anchor="ms", fill=(255,255,255))
    if foot2:
        ff2 = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", int(size*0.042))
        d.text((W//2, H - int(pad_bot*0.20)), foot2, font=ff2, anchor="ms", fill=(170, 170, 170))
    return img.convert("RGB")
