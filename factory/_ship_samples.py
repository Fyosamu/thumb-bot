# -*- coding: utf-8 -*-
"""Ship each finished render into the desktop sample folder at once.

The factory drops out_bio/<slug>.mp4 the moment a script finishes; this
copies it straight into the owner's sample folder, so the videos appear
there one by one while the batch is still rendering instead of all at
the end.  Exits when all six are in place (or after 95 minutes).
"""
import shutil
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out_bio"
ROOT = Path.home() / "Desktop" / "\u062e\u062e\u062e\u06a9\u06a9\u06a9\u062e"
SLUGS = ("beethoven", "beethoven_short", "curie", "curie_short",
         "davinci", "davinci_short")
DEADLINE = time.time() + 95 * 60


def bio_folder() -> Path:
    for d in ROOT.iterdir():
        if d.is_dir() and ("\u0632\u0646\u062f" in d.name or "bio" in d.name.lower()):
            return d
    raise SystemExit(f"bio sample folder not found under {ROOT}")


def stable(path: Path, seen: dict) -> bool:
    """True when ffmpeg is done - two polls with the same size."""
    size = path.stat().st_size
    if seen.get(path.name) == size:
        return True
    seen[path.name] = size
    return False


def main() -> int:
    dst = bio_folder()
    seen: dict = {}
    shipped = set()
    while time.time() < DEADLINE:
        pending = False
        for slug in SLUGS:
            mp4 = OUT / f"{slug}.mp4"
            if not mp4.exists():
                pending = True
                continue
            if not stable(mp4, seen):
                pending = True
                continue
            if slug in shipped:
                continue
            shutil.copy2(mp4, dst / f"{slug}.mp4")
            jpg = OUT / f"{slug}.jpg"
            if jpg.exists():
                shutil.copy2(jpg, dst / f"{slug}.jpg")
            shipped.add(slug)
            print(f"shipped {slug} -> {dst}", flush=True)
        if not pending and len(shipped) == len(SLUGS):
            print("all six samples are in the folder", flush=True)
            return 0
        time.sleep(15)
    print(f"deadline reached - shipped {len(shipped)}/6", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
