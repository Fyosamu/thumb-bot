# -*- coding: utf-8 -*-
"""Re-stamp all six thumbnails without re-rendering the videos.

Two traps this avoids:
- part_number() reads factory.CONTENT, which is the *science* folder
  at import time - beethoven would silently lose its PART badge.
- make_thumbnail() stages its photo beside the dest as <dest>.src.jpg
  and only ever fetches it from Pexels; the render stores it in the
  work folder, so the regen copies it next to the dest first.
Pexels has been unreachable for a while and each dead retry costs ~3
minutes, so with a staged photo in place the network is short-circuited.
"""
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import factory  # noqa: E402

OUT = HERE / "out_bio"
WORK = HERE / "work_bio"
ROOT = Path.home() / "Desktop" / "\u062e\u062e\u062e\u06a9\u06a9\u06a9\u062e"
SLUGS = ("beethoven", "beethoven_short", "curie", "curie_short",
         "davinci", "davinci_short")
SIZES = {"landscape": (1920, 1080), "portrait": (1080, 1920)}


def bio_folder() -> Path:
    for d in ROOT.iterdir():
        if d.is_dir() and ("\u0632\u0646\u062f" in d.name or "bio" in d.name.lower()):
            return d
    raise SystemExit(f"bio sample folder not found under {ROOT}")


def stage_photo(slug: str, dest: Path) -> bool:
    """Copy the render's photo where make_thumbnail's fallback looks."""
    cached = WORK / slug / "thumb.src.jpg"
    if not cached.exists():
        return False
    shutil.copy2(cached, dest.with_suffix(".src.jpg"))
    return True


def main() -> int:
    factory.CONTENT = HERE / "content_bio"     # face photos for THIS channel
    dst = bio_folder()

    # the old renders kept their stock photo in the work folder - stage it
    # as the last-resort fallback; the subject's own face (wiki_photo,
    # cached as <dest>.face.jpg) always wins over stock anyway
    for s in SLUGS:
        stage_photo(s, OUT / f"{s}.jpg")

    for slug in SLUGS:
        script = json.loads(
            (HERE / "content_bio" / f"{slug}.json").read_text(encoding="utf-8"))
        vw, vh = SIZES.get(script.get("orientation", "landscape"),
                           SIZES["landscape"])
        factory.make_thumbnail(script, OUT / f"{slug}.jpg", vw, vh)
        if (OUT / f"{slug}.jpg").exists():
            shutil.copy2(OUT / f"{slug}.jpg", dst / f"{slug}.jpg")
            print(f"{slug}: thumbnail regenerated + shipped", flush=True)
        else:
            print(f"{slug}: thumbnail FAILED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
