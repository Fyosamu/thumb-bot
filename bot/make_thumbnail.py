# -*- coding: utf-8 -*-
"""Build a chess thumbnail (16:9 long / 9:16 short) fully offline.

Source images live in bot/thumbs_src (generated locally, committed to git),
so GitHub Actions never needs an image-generation API key.

Hook + image rotation are stored in state/thumb_index.json so every video
gets a different picture and a different attention hook.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gold_thumb import HOOKS, make  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "thumbs_src")
STATE_DIR = os.path.join(HERE, "..", "state")
INDEX = os.path.join(STATE_DIR, "thumb_index.json")


def _next(key, n):
    os.makedirs(STATE_DIR, exist_ok=True)
    data = {}
    if os.path.exists(INDEX):
        try:
            data = json.load(open(INDEX, encoding="utf-8"))
        except Exception:
            data = {}
    i = (int(data.get(key, -1)) + 1) % max(1, n)
    data[key] = i
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return i


def build(mode="long", out=None, hook_text=None):
    imgs = sorted(glob.glob(os.path.join(SRC, "*.webp")))
    if not imgs:
        raise SystemExit("no source images in %s" % SRC)
    hook_i = _next("hook", len(HOOKS))
    img_i = _next("img_" + mode, len(imgs))
    if out is None:
        out = os.path.join(STATE_DIR, "thumbnail_%s.jpg" % mode)
    path, hook = make(imgs[img_i], out, mode, hook_i, hook_text=hook_text)
    print("%s | %s" % (path, hook))
    return path, hook


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "long"
    build(m)
