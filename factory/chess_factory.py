# -*- coding: utf-8 -*-
"""Render one chess episode for channel 2, on the runner.

A chess episode is a JSON file in content_chess/ that already names the exact
puzzles it uses (they are picked from puzzles_pool.jsonl when the script is
written, never at render time), so a re-render is byte-for-byte predictable
and two episodes can never share a puzzle.

    python chess_factory.py --list  --channel 2
    python chess_factory.py --batch --channel 2 --only chess_part03 chess_part03_short

Everything it produces - <slug>.mp4, <slug>_short.mp4 and both thumbnails -
lands in the channel's out folder, which is exactly what factory/upload.py
picks up.  Nothing here talks to YouTube.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOT = HERE.parent / "bot"
for p in (str(HERE), str(BOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# the Windows box has Arial; the Linux runner gets DejaVu, close enough
# that the shrink-to-fit loops still land the same way
_LINUX_FONTS = {"arialbd.ttf": "DejaVuSans-Bold.ttf",
                "arial.ttf": "DejaVuSans.ttf"}


def _font_path(name: str):
    win = Path(r"C:\Windows\Fonts") / name
    if win.exists():
        return win
    lin = Path("/usr/share/fonts/truetype/dejavu") / _LINUX_FONTS[name]
    return lin if lin.exists() else None


import channels as channel_profiles  # noqa: E402
from board_renderer import render_board  # noqa: E402
from music_lib import get_ffmpeg, make_short, make_video  # noqa: E402

LONG_SEG = 60        # seconds a puzzle is on screen in the long video
SHORT_SEG = 45       # seconds for the vertical Short
BAND_TOP = 0.55      # the thumbnail house style, shared with factory.py
GOLD = (255, 214, 10)


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


HOOKS = (
    "YOU CAN'T SPOT THIS {}",
    "99% MISS THIS {}",
    "YOU'LL NEVER SOLVE THIS {}",
    "CAN YOU SOLVE THIS {}?",
    "NO WAY YOU SEE THIS {}",
    "PROVE YOU CAN FIND THIS {}",
    "YOU'LL CHOKE ON THIS {}",
    "FIND THIS {} — I'LL WAIT",
)


def hook_text(script: dict) -> str:
    """A dare for the thumbnail: 'YOU CAN'T SPOT THIS MATE IN 3'.

    The variant is picked from the slug so the long and its shorts never
    repeat the same line, and regeneration always gives the same result.
    """
    base = str(script.get("thumb_text") or script.get("title", "")).strip().upper()
    key = str(script.get("slug", script.get("title", "")))
    pick = HOOKS[sum(ord(c) for c in key) % len(HOOKS)]
    if base and base not in pick:
        return pick.format(base)
    return pick.format("").replace("  ", " ").strip()


def _edge_mask(w: int, h: int, thick: int, blur: int):
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    steps = 12
    for i in range(steps):
        inset = int(thick * i / steps)
        d.rectangle([inset, inset, w - inset, h - inset],
                    fill=int(255 * (1 - i / steps)))
    d.rectangle([thick, thick, w - thick, h - thick], fill=0)  # true core
    return mask.filter(ImageFilter.GaussianBlur(blur))


def _fire_rim(img) -> None:
    """The approved 11_fire_only style: house layout untouched, only a
    fire rim on the frame.  Cold is pure black and the mask core is a
    true zero, so outside the rim the screen-blend changes nothing."""
    import random
    from PIL import ImageChops, ImageDraw, ImageOps
    w, h = img.size
    glow = _edge_mask(w, h, 90, 14)
    glow = ImageChops.multiply(ImageChops.multiply(glow, glow), glow)
    hot = ImageOps.colorize(glow, (0, 0, 0), (255, 226, 130), mid=(255, 92, 10))
    img.paste(ImageChops.screen(img, hot))
    rim = ImageOps.colorize(_edge_mask(w, h, 9, 3), (0, 0, 0),
                            (255, 250, 200), mid=(255, 150, 30))
    img.paste(ImageChops.screen(img, rim))
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(30):
        side = random.randrange(4)
        if side < 2:
            x = random.randrange(w)
            y = random.randrange(0, h // 5) if side == 0 \
                else random.randrange(h * 4 // 5, h)
        else:
            x = random.randrange(0, w // 6) if side == 2 \
                else random.randrange(w * 5 // 6, w)
            y = random.randrange(h)
        r = random.randrange(2, 7)
        c = random.choice([(255, 150, 30), (255, 225, 95), (255, 90, 12)])
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=c + (random.randrange(120, 255),))


def make_thumb(script: dict, pz: dict, dest: Path, w: int, h: int,
               part: int) -> Path:
    """Board on top, dark band from 55%, bold gold title, PART stamp.

    The stamp goes top-right because YouTube paints the video length over the
    bottom-right corner of every thumbnail.
    """
    from PIL import Image, ImageDraw, ImageFont

    canvas = Image.new("RGB", (w, h), (30, 31, 33))
    band_y = int(h * BAND_TOP)
    if w > h:
        # 16:9 - the board is the subject, so it takes the full height on the
        # left exactly as it does in the video, and the title band rides over
        # its lower edge the way a title bar should.
        side = int(h * 0.96)
        x, y = int(w * 0.035), (h - side) // 2
    else:
        # 9:16 - the board sits entirely above the band so nothing is hidden
        side = int(min(w * 0.94, band_y - int(h * 0.02)))
        x, y = (w - side) // 2, int(h * 0.02)
    board = render_board(pz["fen"], size=side).convert("RGB")
    canvas.paste(board, (x, y))

    draw = ImageDraw.Draw(canvas, "RGBA")

    text = hook_text(script)
    fsize = int(h * (0.085 if w > h else 0.075))
    face = _font_path("arialbd.ttf") or _font_path("arial.ttf")
    face = str(face) if face else None
    font = ImageFont.truetype(face, fsize) if face else ImageFont.load_default()

    lines = textwrap.wrap(text, width=22)[:3]
    # portrait boards are narrow: keep shrinking until the widest line fits
    while face and fsize > 40 and max(
            draw.textlength(line, font=font) for line in lines) > w * 0.92:
        fsize = int(fsize * 0.9)
        font = ImageFont.truetype(face, fsize)
    # the title hugs the bottom with a breathing gap, font size untouched,
    # and the black band is a caption strip riding just above the text
    y = int(h * 0.92 - len(lines) * fsize * 1.12)
    draw.rectangle([0, max(0, y - int(h * 0.035)), w, h], fill=(0, 0, 0, 178))
    for line in lines:
        lw = draw.textlength(line, font=font)
        x = (w - lw) / 2
        draw.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0, 230))
        draw.text((x, y), line, font=font, fill=GOLD + (255,))
        y += int(fsize * 1.12)

    if part:
        m = int(min(w, h) * 0.030)
        psize = int(min(w, h) * 0.055)
        pfont = None
        for cand in (_font_path("arialbd.ttf"), _font_path("arial.ttf")):
            if cand:
                pfont = ImageFont.truetype(str(cand), psize)
                break
        if pfont is None:
            pfont = ImageFont.load_default()
        label = f"PART {part}"
        pad_x, pad_y = psize // 2, psize // 3
        bx2, by1 = w - m, m
        bx1 = bx2 - draw.textlength(label, font=pfont) - pad_x * 2
        by2 = m + psize + pad_y * 2
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=(by2 - by1) // 3,
                               fill=GOLD + (255,))
        draw.text((bx1 + pad_x, by1 + pad_y), label, font=pfont,
                  fill=(8, 8, 12, 255))

    _fire_rim(canvas)

    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, quality=93)
    return dest


def part_number(script: dict, folder: Path) -> int:
    """Episode number; a short carries the same number as its long.

    Sorted numerically: zero padding stops at part9999, and plain string
    sorting would file part10010 between part10001 and part1002."""
    slug = str(script.get("slug", ""))
    stem = re.sub(r"_short\d*$", "", slug)

    def order(s: str) -> int:
        digits = re.sub(r"\D", "", s)
        return int(digits) if digits else 0

    longs = sorted((p.stem for p in folder.glob("*.json")
                    if "_short" not in p.stem), key=order)
    try:
        return longs.index(stem) + 1
    except ValueError:
        return 0


def is_short(slug: str) -> bool:
    """True for every short form: _short, _short2, _short3 ..."""
    return "_short" in slug


def episodes(folder: Path) -> list[tuple[str, list[str]]]:
    """(long slug, every short slug belonging to it) in queue order."""
    stems = sorted(p.stem for p in folder.glob("*.json"))
    out = []
    for stem in stems:
        if is_short(stem):
            continue
        shorts = [s for s in stems if s.startswith(stem + "_short")]
        out.append((stem, shorts))
    return out


def build_one(slug: str, prof: dict, work: Path, ff: str) -> Path | None:
    """Render one script (long or short) into the channel's out folder."""
    is_short_slug = is_short(slug)
    script = load(prof["content"] / f"{slug}.json")
    puzzles = script["puzzles"]
    out_dir = prof["out"]
    out_dir.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    tag = f"{script['slug']}"
    part = part_number(script, prof["content"])

    if is_short_slug:
        pz = puzzles[0]
        raw = make_short(pz, str(work), tag, 1, ff=ff, seg=SHORT_SEG)
        thumb = make_thumb(script, pz, out_dir / f"{slug}.jpg", 1080, 1920, part)
    else:
        raw = make_video(puzzles, str(work), tag, seg=LONG_SEG, ff=ff)
        thumb = make_thumb(script, puzzles[0], out_dir / f"{slug}.jpg",
                           1920, 1080, part)

    dest = out_dir / f"{slug}.mp4"
    if Path(raw).resolve() != dest.resolve():
        shutil.move(str(raw), str(dest))
    print(f"  rendered {slug} -> {dest.name} "
          f"({dest.stat().st_size/1e6:.1f} MB, thumb {thumb.name})")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--channel", default=None)
    args = ap.parse_args()

    prof = channel_profiles.profile(args.channel)
    channel_profiles.ensure(prof)
    folder = Path(prof["content"])
    eps = episodes(folder)
    print(f"channel {prof['channel']} ({prof['label']}) -> {folder.name}/ "
          f"({len(eps)} episodes)")

    if args.list:
        for lng, sht in eps:
            s = load(folder / f"{lng}.json")
            print(f"  {lng:24} puzzles={len(s['puzzles']):3}  "
                  f"{str(s.get('title',''))[:52]}")
        return 0

    todo = []
    for lng, shts in eps:
        todo.append(lng)
        todo.extend(shts)
    if args.only:
        want = set(args.only.split())
        todo = [t for t in todo if t in want]
    if not args.batch and not args.only:
        print("pass --batch or --only")
        return 1

    work = Path(prof["work"])
    ff = get_ffmpeg()
    for slug in todo:
        if not (folder / f"{slug}.json").exists():
            print(f"  SKIP no script {slug}")
            continue
        build_one(slug, prof, work, ff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
