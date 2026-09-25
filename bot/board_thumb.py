# -*- coding: utf-8 -*-
"""16:9 chess thumbnail from a REAL puzzle position.

- gold hook text glued to the very top
- real board with the solution arrow (the sacrifice move)
- move number notation + rating pill + difficulty label
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gold_thumb import GOLD_MID, GOLD_TOP, gold_gradient, load_font, wrap  # noqa: E402
import board_renderer as br  # noqa: E402

W, H = 1280, 720
POOL = os.path.join(HERE, "..", "puzzles_pool.jsonl")

IDX_FILE = os.path.join(HERE, "..", "state", "board_thumb_index.json")


def load_pool(n=400):
    out = []
    try:
        with open(POOL, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    p = json.loads(line)
                except Exception:
                    continue
                if p.get("rating", 0) >= 1900 and p.get("uci"):
                    out.append(p)
                if len(out) >= n:
                    break
    except FileNotFoundError:
        pass
    return out


def next_puzzle():
    pool = load_pool()
    if not pool:
        raise SystemExit("puzzles_pool.jsonl not found or empty")
    os.makedirs(os.path.dirname(IDX_FILE), exist_ok=True)
    i = -1
    if os.path.exists(IDX_FILE):
        try:
            i = int(json.load(open(IDX_FILE, encoding="utf-8")).get("p", -1))
        except Exception:
            i = -1
    i = (i + 1) % len(pool)
    json.dump({"p": i}, open(IDX_FILE, "w", encoding="utf-8"))
    return pool[i]


def difficulty(rating):
    if rating > 2355:
        return "VERY HARD"
    if rating > 2000:
        return "HARD"
    return "MEDIUM"


def move_label(fen, uci):
    try:
        import chess
        b = chess.Board(fen)
        m = chess.Move.from_uci(uci[0])
        san = b.san(m)
        no = b.fullmove_number
        prefix = str(no) + ("." if b.turn == chess.WHITE else "...")
        return prefix + san, no
    except Exception:
        return uci[0], 0


def fit(img, w, h):
    if img.width == w and img.height == h:
        return img
    return img.resize((w, h), Image.LANCZOS)


def vignette(w, h):
    v = Image.new("L", (w, h), 0)
    ImageDraw.Draw(v).ellipse([-w * 0.3, -h * 0.4, w * 1.3, h * 1.4], fill=255)
    return v.filter(ImageFilter.GaussianBlur(120))


def draw_gold_block(base, text, y0, maxw, size_hint=None, align="center", x_left=None):
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    size = size_hint or int(W * 0.072)
    while size >= 34:
        f = load_font(size)
        lines = wrap(probe, text, f, maxw)
        if len(lines) * int(size * 1.06) <= int(H * 0.28):
            break
        size -= 4
    font = load_font(size)
    lines = wrap(probe, text, font, maxw)
    lh = int(size * 1.06)
    pad_x, pad_y, gap = 20, 10, 8
    boxes = []
    total = 0
    for ln in lines:
        tw = probe.textlength(ln, font=font)
        bw, bh = int(tw) + pad_x * 2, lh + pad_y * 2
        boxes.append((ln, int(tw), bw, bh))
        total += bh + gap
    total -= gap

    sh = Image.new("L", (W, H), 0)
    shd = ImageDraw.Draw(sh)
    yy = y0
    for ln, tw, bw, bh in boxes:
        bx = (x_left if x_left is not None else (W - bw) // 2) + 6
        shd.rounded_rectangle([bx, yy + 6, bx + bw, yy + bh + 6], radius=9, fill=255)
        yy += bh + gap
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    base.paste((0, 0, 0), (0, 0), sh)

    d = ImageDraw.Draw(base)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    yy = y0
    for ln, tw, bw, bh in boxes:
        bx = x_left if x_left is not None else (W - bw) // 2
        d.rounded_rectangle([bx, yy, bx + bw, yy + bh], radius=9,
                            fill=(0, 0, 0))
        md.text((bx + pad_x, yy + pad_y - int(lh * 0.14)), ln, font=font, fill=255)
        yy += bh + gap

    base.paste(gold_gradient(W, H), (0, 0), mask)
    shine = mask.filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.25))
    base.paste((255, 255, 255), (0, 0), shine)
    return total


def pill(d, cx, cy, text, font, outline=GOLD_MID, fill=(0, 0, 0), pad_x=22, pad_y=10):
    tw = d.textlength(text, font=font)
    x0, y0 = cx - tw / 2 - pad_x, cy - font.size / 2 - pad_y
    x1, y1 = cx + tw / 2 + pad_x, cy + font.size / 2 + pad_y
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=fill, outline=outline, width=3)
    d.text((cx, cy), text, font=font, anchor="mm", fill=GOLD_TOP)
    return y1


def make(puzzle, out, hook_text):
    fen, uci = puzzle["fen"], puzzle["uci"]
    rating = int(puzzle.get("rating", 2000))
    label, move_no = move_label(fen, uci)
    diff = difficulty(rating)

    canvas = Image.new("RGB", (W, H), (17, 18, 20))
    d0 = ImageDraw.Draw(canvas)
    for i in range(H):
        k = i / H
        d0.line([(0, i), (W, i)], fill=(int(24 - 12 * k), int(25 - 12 * k), int(28 - 13 * k)))

    # board with solution arrow
    bimg = br.render_board(fen, size=430,
                           sol=[uci[0][:2], uci[0][2:]],
                           last=[uci[0][:2], uci[0][2:]])
    bx = W - bimg.width - 24
    by = H - bimg.height - 20
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [bx + 8, by + 10, bx + bimg.width + 8, by + bimg.height + 10],
        radius=14, fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    canvas = canvas.convert("RGBA")
    canvas = Image.alpha_composite(canvas, shadow)
    canvas = canvas.convert("RGB")
    if bimg.mode == "RGBA":
        board_rgb = Image.new("RGB", bimg.size, (17, 18, 20))
        board_rgb.paste(bimg, (0, 0), bimg.split()[3])
        bimg = board_rgb
    else:
        bimg = bimg.convert("RGB")
    canvas.paste(bimg, (bx, by))

    # text glued to the very top
    draw_gold_block(canvas, hook_text, y0=8, maxw=W - 60)

    # left column: move notation + rating + difficulty
    d = ImageDraw.Draw(canvas)
    big = load_font(72)
    draw_gold_block(canvas, label, y0=250, maxw=560, size_hint=72, x_left=36)

    pill(d, 190, 420, "RATING  %d" % rating, load_font(40))
    pill(d, 190, 500, diff, load_font(44), outline=(255, 255, 255))
    pill(d, 190, 580, "WHITE TO MOVE" if fen.split()[1] == "w" else "BLACK TO MOVE",
         load_font(34), outline=(120, 170, 255))

    vig = vignette(W, H)
    canvas = Image.composite(canvas, Image.new("RGB", (W, H), (4, 4, 5)), vig)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    canvas.save(out, quality=95)
    return out, hook_text, label, rating, diff


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\USER\Desktop\chess_sample\sample_board.jpg"
    hook = sys.argv[2] if len(sys.argv) > 2 else "YOU CAN'T SOLVE THIS PUZZLE"
    p = next_puzzle()
    print(make(p, out, hook))
