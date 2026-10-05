# -*- coding: utf-8 -*-
"""Pick tomorrow's episode for the daily upload bot.

The bot must publish exactly one episode a day, so it needs a cursor that
walks through content/ in a stable order instead of guessing from upload
state (the ledger is keyed by sha256, which does not exist before render).

    python pick.py next      print "<long> <long>_short" for today
    python pick.py advance   move the cursor on after a successful upload

The cursor lives in state/cursor.json and is committed back with the rest
of the state, so restarting a run never repeats or skips an episode.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import channels as channel_profiles

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content"
STATE = HERE / "state"
CURSOR = STATE / "cursor.json"


def episodes() -> list[str]:
    """Long-form slugs in a stable order; a long leads its own short."""
    slugs = sorted(p.stem for p in CONTENT.glob("*.json"))
    longs = [s for s in slugs if not s.endswith("_short")]
    return [s for s in longs if f"{s}_short" in slugs] + \
        [s for s in longs if f"{s}_short" not in slugs]


def cursor() -> int:
    if not CURSOR.exists():
        return 0
    try:
        return int(json.loads(CURSOR.read_text(encoding="utf-8")).get("i", 0))
    except Exception:
        return 0


def main() -> int:
    global CONTENT, STATE, CURSOR
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["next", "advance", "status"])
    ap.add_argument("--channel", default=None,
                    help="channel profile: 1 = science, 3 = biography - "
                         "each walks its own queue and its own cursor")
    args = ap.parse_args()

    # every channel has its own script folder and its own cursor
    prof = channel_profiles.profile(args.channel)
    CONTENT = prof["content"]
    CURSOR = prof["cursor"]
    STATE = CURSOR.parent
    channel_profiles.ensure(prof)

    eps = episodes()
    i = cursor()

    if args.action == "status":
        print(f"channel {prof['channel']} ({prof['label']}) "
              f"cursor {i}/{len(eps)} in {CONTENT.name}/")
        return 0

    if args.action == "advance":
        STATE.mkdir(parents=True, exist_ok=True)
        CURSOR.write_text(json.dumps({"i": i + 1, "of": len(eps)}, indent=2),
                          encoding="utf-8")
        print(f"advanced {i} -> {i + 1} of {len(eps)}")
        return 0

    if not eps:
        # empty queue is not an error - the job just has nothing to do today
        print("no scripts in content/", file=sys.stderr)
        pair = ""
    elif i >= len(eps):
        print(f"cursor past the end ({i}/{len(eps)}) - nothing left",
              file=sys.stderr)
        pair = ""
    else:
        slug = eps[i]
        pair = f"{slug} {slug}_short" if f"{slug}_short" in \
            [p.stem for p in CONTENT.glob("*.json")] else slug

    # GitHub Actions reads this file as the step's outputs
    gh_out = Path(__import__("os").environ.get("GITHUB_OUTPUT", ""))
    if gh_out.is_file():
        with gh_out.open("a", encoding="utf-8") as fh:
            fh.write(f"slugs={pair}\nepisodes={len(eps)}\nindex={i}\n"
                     f"channel={prof['channel']}\n")
    print(f"[{prof['label']}] {pair or '(queue empty)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
