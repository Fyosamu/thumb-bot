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
import shutil
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOT = HERE.parent / "bot"
for p in (str(HERE), str(BOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import channels as channel_profiles  # noqa: E402
from board_renderer import render_board  # noqa: E402
from music_lib import get_ffmpeg, make_short, make_video  # noqa: E402

LONG_SEG = 60        # seconds a puzzle is on screen in the long video
SHORT_SEG = 45       # seconds for the vertical Short
BAND_TOP = 0.55      # the thumbnail house style, shared with factory.py
GOLD = (255, 214, 10)


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def make_thumb(script: dict, pz: dict, dest: Path, w: int, h: int,
               part: int) -> Path:
    """Board on top, dark band from 55%, bold gold title, PART stamp.

    The stamp goes top-right because YouTube paints the video length over the
    bottom-right corner of every thumbnail.
    """
    from PIL import Image, ImageDraw, ImageFont

    canvas = Image.new("RGB", (w, h), (30, 31, 33))
    side = int(min(w, h * 0.92) * 0.92)
    board = render_board(pz["fen"], size=side).convert("RGB")
    canvas.paste(board, ((w - side) // 2, int(h * 0.02)))

    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle([0, int(h * BAND_TOP), w, h], fill=(0, 0, 0, 178))

    text = str(script.get("thumb_text") or script.get("title", ""))
    fsize = int(h * (0.085 if w > h else 0.075))
    font = None
    for fp in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if Path(fp).exists():
            font = ImageFont.truetype(fp, fsize)
            break
    if font is None:
        font = ImageFont.load_default()

    lines = textwrap.wrap(text.upper(), width=22)[:3]
    y = int(h * 0.60)
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
        for fp in (r"C:\Windows\Fonts\arialbd.ttf",
                   r"C:\Windows\Fonts\arial.ttf"):
            if Path(fp).exists():
                pfont = ImageFont.truetype(fp, psize)
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

    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, quality=93)
    return dest


def part_number(script: dict, folder: Path) -> int:
    """Episode number; a short carries the same number as its long."""
    slug = str(script.get("slug", ""))
    stem = slug[:-6] if slug.endswith("_short") else slug
    longs = sorted(p.stem for p in folder.glob("*.json")
                   if not p.stem.endswith("_short"))
    try:
        return longs.index(stem) + 1
    except ValueError:
        return 0


def episodes(folder: Path) -> list[tuple[str, str | None]]:
    """(long slug, short slug or None) in queue order."""
    out = []
    for p in sorted(folder.glob("*.json")):
        if p.stem.endswith("_short"):
            continue
        short = p.stem + "_short"
        out.append((p.stem, short if (folder / f"{short}.json").exists() else None))
    return out


def build_one(slug: str, prof: dict, work: Path, ff: str) -> Path | None:
    """Render one script (long or short) into the channel's out folder."""
    is_short = slug.endswith("_short")
    script = load(prof["content"] / f"{slug}.json")
    puzzles = script["puzzles"]
    out_dir = prof["out"]
    out_dir.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    tag = f"{script['slug']}"
    part = part_number(script, prof["content"])

    if is_short:
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
    for lng, sht in eps:
        todo.append(lng)
        if sht:
            todo.append(sht)
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
