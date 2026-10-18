import json, glob, os
d = os.path.dirname(os.path.abspath(__file__))
for f in sorted(glob.glob(os.path.join(d, "*.json"))):
    with open(f, encoding="utf-8") as fh:
        j = json.load(fh)
    scenes = j["scenes"]
    wc = sum(len(s["narration"].split()) for s in scenes)
    print(os.path.basename(f), "| scenes:", len(scenes), "| words:", wc,
          "| min/max:", min(len(s["narration"].split()) for s in scenes),
          max(len(s["narration"].split()) for s in scenes),
          "| keys:", list(j.keys()))
