# -*- coding: utf-8 -*-
import glob
import json
import os

for p in sorted(glob.glob(r"C:\Users\USER\Desktop\chess-repo\factory\content_bio\*.json")):
    n = os.path.basename(p)
    if n.startswith("b0") or n.startswith("__"):
        continue
    d = json.load(open(p, encoding="utf-8"))
    print(f"{n:26} voice={d.get('voice', '?')}")
