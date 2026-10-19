# -*- coding: utf-8 -*-
"""Daily reel robot for the web-design ad project.

    python reel_robot.py                # today's reel (day index = days since 2026-01-01)
    python reel_robot.py --index 42     # a specific episode
    python reel_robot.py --index 42 --bank-fallback

Reads bank.jsonl, renders the episode through the exact same factory.py
shorts pipeline (captions, mellow bed at 0.10, portrait 1080x1920),
overwrites the thumbnail with the custom ad style, and drops a ready-to-post
pack into out/: <slug>.mp4 + <slug>.jpg + caption.txt.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE / "bank.jsonl"
WORK = HERE / "_work"
OUT = HERE / "out"
FACTORY = HERE.parent.parent / "factory" / "factory.py"
EPOCH = dt.date(2026, 1, 1)


def bank_line(index: int) -> dict:
    if not BANK.exists():
        subprocess.run([sys.executable, str(HERE / "gen_scripts.py")], check=True)
    with open(BANK, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == index:
                return json.loads(line)
    raise SystemExit(f"bank has no line {index}")


def main(argv) -> int:
    args = list(argv[1:])
    fallback = "--bank-fallback" in args
    if "--index" in args:
        index = int(args[args.index("--index") + 1])
    else:
        index = (dt.date.today() - EPOCH).days

    n = sum(1 for _ in open(BANK, encoding="utf-8")) if BANK.exists() else 0
    if n == 0:
        subprocess.run([sys.executable, str(HERE / "gen_scripts.py")], check=True)
        n = sum(1 for _ in open(BANK, encoding="utf-8"))
    if index >= n:
        if not fallback:
            raise SystemExit(f"index {index} >= bank size {n} "
                             "(use --bank-fallback to wrap around)")
        index %= n

    script = bank_line(index)
    WORK.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    src = WORK / f"{script['slug']}.json"
    src.write_text(json.dumps(script, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"[reel] ep{index} {script['slug']} template={script.get('template')}")

    rc = subprocess.run([sys.executable, str(FACTORY), "--render", str(src)]).returncode
    if rc != 0:
        return rc

    rendered = HERE.parent.parent / "factory" / "out" / f"{script['slug']}.mp4"
    if not rendered.exists():
        raise SystemExit(f"render produced nothing at {rendered}")
    mp4 = OUT / rendered.name
    import shutil
    shutil.copy2(rendered, mp4)

    subprocess.run([sys.executable, str(HERE / "make_thumb.py"), str(src),
                    str(OUT / f"{script['slug']}.jpg")], check=True)

    (OUT / "caption.txt").write_text(
        script["title"] + "\n\n" + script["description"], encoding="utf-8")
    print(f"[reel] ready: {mp4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
