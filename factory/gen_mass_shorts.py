# -*- coding: utf-8 -*-
"""Derive a portrait Short script from every long mass-bank episode.

gen_mass writes landscape longs only; the daily bot's pace is one long
plus its Short a day, so every long needs `<slug>_short.json` before the
cursor reaches it.  This pass is pure disk work - no network - so it can
run before every daily batch and keep the bank pair-complete forever.

The derived Short mirrors the hand-written short shape (portrait, ~115
words, 5-7 bite scenes) using the long's own opening narration.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
# channel folder -> mass-bank file prefix
BANKS = [(HERE / "content", "m"), (HERE / "content_bio", "b")]
CHUNK = 18          # words per Short scene - bite sized, one stock clip each
TARGET = 115        # total Short words, inside a 60s read


def derive(long_path: Path, short_path: Path) -> bool:
    doc = json.loads(long_path.read_text(encoding="utf-8"))
    scenes = doc.get("scenes") or []
    if not scenes:
        return False

    words: list[str] = []
    for sc in scenes:
        words += str(sc.get("narration", "")).split()
        if len(words) >= TARGET:
            break
    words = words[:TARGET]
    if len(words) < 60:
        return False

    stocks = [sc.get("stock", "") for sc in scenes]
    out_scenes = []
    for i in range(0, len(words), CHUNK):
        out_scenes.append({"stock": stocks[(i // CHUNK) % len(stocks)],
                           "narration": " ".join(words[i:i + CHUNK])})

    title = str(doc.get("title", long_path.stem)).strip()
    desc = str(doc.get("description", ""))[:4600]
    if "#Shorts" not in desc:
        desc += "\n\n#Shorts"
    tags = list(doc.get("tags", []))[:39]
    if not any(str(t).lower() == "#shorts" for t in tags):
        tags.append("#Shorts")
    short = {
        "slug": long_path.stem + "_short",
        "title": (title[:93] + " #Shorts") if len(title) > 90
                 else (title + " #Shorts"),
        "orientation": "portrait",
        "voice": doc.get("voice", "en-US-AvaMultilingualNeural"),
        "thumb_text": doc.get("thumb_text", ""),
        "thumb_stock": doc.get("thumb_stock", ""),
        "description": desc,
        "tags": tags,
        "scenes": out_scenes,
        "_derived": 3,
        "_summary_of": long_path.stem,
        "_words": len(words),
    }
    short_path.write_text(
        json.dumps(short, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return True


def main() -> int:
    made = 0
    for folder, prefix in BANKS:
        if not folder.is_dir():
            continue
        for long in sorted(folder.glob(f"{prefix}[0-9][0-9][0-9][0-9][0-9].json")):
            short = long.with_name(long.stem + "_short.json")
            if short.exists():
                # shorts from an older generator carry wrong titles and a
                # two-scene cut - only keep the ones this tool stamped
                try:
                    old = json.loads(short.read_text(encoding="utf-8"))
                    if old.get("_derived") == 3:
                        continue
                except Exception:                       # noqa: BLE001
                    pass
            if derive(long, short):
                made += 1
    print(f"derived {made} short scripts", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
