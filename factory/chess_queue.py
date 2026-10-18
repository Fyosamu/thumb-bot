# -*- coding: utf-8 -*-
"""Grow the chess queue toward 50,000 ready videos.

One episode = one long (12 puzzles) + three shorts (one puzzle each), so
12,500 episodes is exactly 50,000 files sitting in content_chess/ waiting
for the daily renderer.  The pool is cycled deterministically: episode k
takes puzzles (k*12 + i) % pool, which keeps re-runs byte-identical and
the difficulty spread honest across the whole range.

    python chess_queue.py            # top the queue up to 12500 episodes
    python chess_queue.py 20000      # aim at a different episode count
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = HERE.parent / "puzzles_pool.jsonl"
CONTENT = HERE / "content_chess"

TARGET_EPISODES = 12500        # 12,500 x (1 long + 3 shorts) = 50,000 videos
PER_LONG = 12

SUBTITLES = (
    "Calculate Three Moves Deep", "Find the Right Idea",
    "Spot The Tactical Shot", "See The Mate Before It Happens",
    "The Combination Nobody Sees", "Read The Position Properly",
    "Find The Only Move", "Punish The Blunder",
    "The Quiet Move That Wins", "Convert The Advantage",
    "Defend And Strike Back", "Hunt The King",
    "The Sacrifice That Works", "Outcalculate The Opponent",
    "Find The Draw Nobody Sees", "Break The Fortress",
)

# first theme that matches decides the thumbnail dare, best-first
THEME_LABELS = (
    ("mateIn2", "MATE IN 2"), ("mateIn3", "MATE IN 3"),
    ("mateIn4", "MATE IN 4"), ("mateIn5", "MATE IN 5"),
    ("smotheredMate", "SMOTHERED MATE"), ("backRankMate", "BACK RANK"),
    ("epauletteMate", "EPAULETTE MATE"),
    ("fork", "FORK"), ("pin", "PIN"), ("skewer", "SKEWER"),
    ("sacrifice", "SACRIFICE"), ("discoveredAttack", "DISCOVERED ATTACK"),
    ("deflection", "DEFLECTION"), ("attraction", "ATTRACTION"),
    ("promotion", "PROMOTION"), ("endgame", "ENDGAME"),
    ("opening", "OPENING"), ("kingsideAttack", "KINGSIDE ATTACK"),
    ("crushing", "CRUSHING"), ("middlegame", "MIDDLEGAME"),
)

TAGS = ["chess", "chess puzzles", "tactics", "chess tactics", "puzzle",
        "calculation", "mating patterns", "chess training", "endgame",
        "chess improvement", "positional chess", "chess combination",
        "chess club", "solve chess", "grandmaster puzzles"]

LONG_DESC = ("Twelve puzzles, one after another, each with a single best "
             "move. Every position comes from a real game and is rated "
             "between {lo} and {hi}, so the difficulty stays honest from "
             "the first board to the last.\n\nPause on each board and find "
             "the move before you read on. The answers are posted in the "
             "comments of the next episode.\n\nMade with AI "
             "assistance.\n\n#chess #chesstactics #chesspuzzles #tactics "
             "#chesstraining #endgame #calculation #chessclub")
SHORT_DESC = ("One position from the full episode. Find the best move, "
              "then solve the other eleven in the long version.\n\nMade "
              "with AI assistance.\n\n#chess #chesstactics "
              "#chesspuzzles #shorts")


def label_for(puzzles: list[dict]) -> str:
    seen: set[str] = set()
    for pz in puzzles:
        seen.update(pz.get("themes") or ())
    for key, text in THEME_LABELS:
        if key in seen:
            return text
    return "CHESS PUZZLES"


def main() -> int:
    target = int(sys.argv[1]) if len(sys.argv) > 1 else TARGET_EPISODES
    pool = [json.loads(line) for line in
            POOL.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not pool:
        print("pool is empty")
        return 1
    have = []
    for p in CONTENT.glob("chess_part*.json"):
        if "_short" in p.stem:
            continue
        tail = p.stem[len("chess_part"):]
        if tail.isdigit():
            have.append(int(tail))
    start = (max(have) if have else 0) + 1
    print(f"{len(have)} episodes in place, pool {len(pool)}, "
          f"extending from part{start:04d} to {target}")

    CONTENT.mkdir(parents=True, exist_ok=True)
    written = 0
    for k in range(start - 1, target):
        part = k + 1
        picks = [pool[(k * PER_LONG + i) % len(pool)] for i in range(PER_LONG)]
        label = label_for(picks)
        sub = SUBTITLES[k % len(SUBTITLES)]
        title = f"12 Chess Puzzles: {sub} (Part {part})"
        ratings = [pz["rating"] for pz in picks]
        long_doc = {
            "slug": f"chess_part{part:04d}",
            "title": title,
            "orientation": "landscape",
            "thumb_text": label,
            "description": LONG_DESC.format(lo=min(ratings), hi=max(ratings)),
            "tags": list(TAGS),
            "puzzles": picks,
        }
        path = CONTENT / f"chess_part{part:04d}.json"
        path.write_text(json.dumps(long_doc, indent=2, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        written += 1
        for si, pz in enumerate(picks[:3], start=1):
            suffix = "" if si == 1 else f"#{si} "
            short_doc = {
                "slug": f"chess_part{part:04d}_short{'' if si == 1 else si}",
                "title": f"{title} {suffix}#Shorts".replace("  ", " "),
                "orientation": "portrait",
                "thumb_text": label,
                "description": SHORT_DESC,
                "tags": list(TAGS),
                "puzzles": [pz],
            }
            name = f"chess_part{part:04d}_short{'' if si == 1 else si}.json"
            (CONTENT / name).write_text(
                json.dumps(short_doc, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
            written += 1
        if part % 500 == 0:
            print(f"  part{part:04d} ({written} files)", flush=True)
    print(f"done: {target} episodes = {target * 4} videos in {CONTENT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
