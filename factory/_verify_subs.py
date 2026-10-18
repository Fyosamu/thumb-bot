# -*- coding: utf-8 -*-
"""Verify the burned subtitles of one render: no overlaps, clean handoff.

    python _verify_subs.py <slug> [--channel 1|2|3]

Without --channel it walks the science folders (the historical default).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(r"C:\Users\USER\Desktop\chess-repo\factory")
sys.path.insert(0, str(HERE))
import factory  # noqa: E402
import channels as channel_profiles  # noqa: E402

ch = next((a.split("=", 1)[1] for a in sys.argv[1:]
           if a.startswith("--channel=")), None)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
slug = args[0] if args else "cold_short"
if ch:
    prof = channel_profiles.profile(ch)
    CONTENT, WORK, OUT = prof["content"], prof["work"], prof["out"]
else:
    CONTENT, WORK, OUT = HERE / "content", HERE / "work", HERE / "out"
orientation = "portrait" if "_short" in slug else "landscape"
vw, vh = (1080, 1920) if orientation == "portrait" else (1920, 1080)
work = WORK / slug

script = json.loads((CONTENT / f"{slug}.json").read_text(encoding="utf-8"))
voices = sorted((work / "voice").glob("*.mp3"))
durs = [factory.duration_of(v) for v in voices]
voices, durs = factory.normalize_length(voices, durs, work, orientation)
caps = factory.make_captions(script, durs, work, vw, vh, orientation)

bad = 0
for i, boxes in enumerate(caps):
    for a, b in zip(boxes, boxes[1:]):
        if b[1] < a[2]:
            print(f"OVERLAP scene {i}: {a[2]:.3f} > {b[1]:.3f}")
            bad += 1
print(f"{sum(len(b) for b in caps)} boxes, overlaps: {bad}, "
      f"total {sum(durs):.1f}s")

segs = [0.0]
for d in durs:
    segs.append(segs[-1] + d)
b0, b1 = caps[0][0], caps[0][1]
picks = [
    ("a_first", segs[0] + b0[1] + 0.4),
    ("b_handoff_last", segs[0] + b0[2] - 0.02),
    ("c_handoff_next", segs[0] + b1[1] + 0.03),
    ("d_scene_edge", segs[1] - 0.05),
    ("e_scene2_start", segs[1] + 0.08),
]
tmp = Path(r"C:\Users\USER\AppData\Local\Temp\subcheck")
tmp.mkdir(exist_ok=True)
for name, t in picks:
    dest = tmp / f"{name}.png"
    subprocess.run([factory.FFMPEG, "-y", "-ss", f"{t:.3f}", "-i",
                    str(HERE / "out" / f"{slug}.mp4"),
                    "-frames:v", "1", str(dest)], capture_output=True)
    print(f"{name}: t={t:.2f} -> {dest.name} ({dest.exists()})")
