# -*- coding: utf-8 -*-
"""Derive a 9:16 summary Short from every queued long script.

For each content/<slug>.json we write content/<slug>_short.json holding a
condensed version of the same story: the hook, a few evenly spaced beats,
and the payoff.  Same voice, same visuals as the topic, roughly a minute.

Usage:
    python make_shorts.py            # build every missing short
    python make_shorts.py --force    # rebuild even if one exists
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content"

# ~130 words is about a minute at Ava's rate, and keeps us safely under the
# 3-minute ceiling YouTube needs to route a video into the Shorts feed.
WORD_BUDGET = 130
MAX_MIDDLE = 4


def is_long(slug: str) -> bool:
    return not slug.endswith("_short")


def pick_scenes(scenes: list[dict]) -> list[dict]:
    """Hook + evenly spaced middle beats + payoff, inside the word budget."""
    n = len(scenes)
    words = [len(s["narration"].split()) for s in scenes]

    if n <= 3:
        chosen = list(range(n))
    else:
        used = words[0] + words[-1]
        chosen = [0]
        middle = list(range(1, n - 1))
        # spread the picks across the body instead of taking the first four
        want = min(MAX_MIDDLE, len(middle))
        step = max(1, len(middle) // want)
        picked = 0
        for i in range(0, len(middle), step):
            if picked >= want:
                break
            if used + words[middle[i]] > WORD_BUDGET:
                continue
            chosen.append(middle[i])
            used += words[middle[i]]
            picked += 1
        chosen.append(n - 1)

    chosen = sorted(set(chosen))
    out = [dict(scenes[i]) for i in chosen]
    return trim_to_budget(out, WORD_BUDGET)


def sentences(text: str) -> list[str]:
    parts, buf = [], ""
    for word in text.split():
        buf += (" " if buf else "") + word
        if word.endswith((".", "!", "?", ":")):
            parts.append(buf)
            buf = ""
    if buf:
        parts.append(buf)
    return parts


def trim_to_budget(scenes: list[dict], budget: int) -> tuple[list[dict], int]:
    """Keep every chosen beat but cut its narration down to whole sentences.

    A Short has to stay under a minute, and the long's opening scene alone
    can run past that, so each beat is reduced to as many whole sentences
    as still fit.  The first and the last beat always keep one sentence,
    because a Short without its hook or its payoff is just a fragment.
    """
    keep: list[dict] = []
    spent = 0
    last = len(scenes) - 1
    for i, scene in enumerate(scenes):
        edge = i in (0, last)
        room = budget - spent
        taken: list[str] = []
        for sent in sentences(scene["narration"]):
            cost = len(sent.split())
            if taken:
                if cost > room:
                    break
            elif not edge:
                break                       # a middle beat that does not
                                            # fit is simply dropped
            taken.append(sent)
            room -= cost
        if not taken:
            continue
        keep.append({**scene, "narration": " ".join(taken)})
        spent += sum(len(s.split()) for s in taken)
    return keep, spent


def make_short(meta: dict) -> dict:
    scenes, words = pick_scenes(meta["scenes"])
    title = meta["title"].strip()
    if not title.lower().endswith("#shorts"):
        title = f"{title} #Shorts"
    return {
        **meta,
        "slug": f"{meta['slug']}_short",
        "title": title,
        "orientation": "portrait",
        "description": (
            f"{scenes[0]['narration']}\n\n"
            f"{scenes[-1]['narration']}\n\n"
            f"Made with AI assistance.\n\n{meta.get('description', '').strip()}"
        )[:4900],
        "tags": list(dict.fromkeys(list(meta.get("tags", []))
                                   + ["shorts", "youtube shorts"]))[:40],
        "scenes": scenes,
        "_summary_of": meta["slug"],
        "_words": words,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--prefix", default="",
                    help="only touch slugs starting with this, e.g. m0 - "
                         "keeps hand-written shorts from being rebuilt")
    args = ap.parse_args()

    made = 0
    for path in sorted(CONTENT.glob("*.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        slug = meta.get("slug", path.stem)
        if not is_long(slug):
            continue
        if args.prefix and not slug.startswith(args.prefix):
            continue
        dest = CONTENT / f"{slug}_short.json"
        if dest.exists() and not args.force:
            continue
        short = make_short(meta)
        dest.write_text(json.dumps(short, indent=2, ensure_ascii=False),
                        encoding="utf-8")
        made += 1
        print(f"  {slug:24s} -> {len(short['scenes'])} scenes, "
              f"{short['_words']} words | {short['title'][:56]}")

    print(f"\n{made} shorts written ({len(list(CONTENT.glob('*_short.json')))} "
          f"total in queue)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
