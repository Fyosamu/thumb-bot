# -*- coding: utf-8 -*-
"""One-off: render one thumbnail per template into _work/ for visual QA."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
lines = (HERE / "bank.jsonl").read_text(encoding="utf-8").splitlines()
seen = {}
for ln in lines:
    s = json.loads(ln)
    if s["template"] not in seen:
        seen[s["template"]] = s
    if len(seen) == 6:
        break
(HERE / "_work").mkdir(exist_ok=True)
for tpl, s in seen.items():
    p = HERE / "_work" / (s["slug"] + ".json")
    p.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    subprocess.run([sys.executable, str(HERE / "make_thumb.py"), str(p),
                    str(HERE / "_work" / f"thumb_{tpl}.jpg")], check=True)
print("thumbs done:", ", ".join(seen))
