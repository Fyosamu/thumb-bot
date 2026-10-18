# -*- coding: utf-8 -*-
"""One-frame caption position check: where does the yellow text sit?"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image

mp4 = sys.argv[1]
at = sys.argv[2] if len(sys.argv) > 2 else "20"
out = os.path.join(os.environ["TEMP"], "caption_check.png")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", at, "-i", mp4,
                "-frames:v", "1", out], check=True)
im = Image.open(out)
w, h = im.size
a = np.asarray(im.convert("RGB")).astype(int)
yellow = ((a[:, :, 0] > 200) & (a[:, :, 1] > 170) & (a[:, :, 2] < 90)) \
    .sum(axis=1)
rows = np.nonzero(yellow)[0]
print("canvas", w, h)
if len(rows):
    center = ((rows.min() + rows.max()) / 2) / h * 100
    print(f"caption rows {rows.min()}..{rows.max()} -> center {center:.1f}%")
else:
    print("no yellow text on this frame")
