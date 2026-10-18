# -*- coding: utf-8 -*-
"""Verify the runner's daily uploads are actually live on YouTube and
print how big the pushed banks are."""
import json
import subprocess
import urllib.parse
import urllib.request

videos = [
    ("chess", "https://www.youtube.com/watch?v=mjdOCI5cYSw"),
    ("science", "https://www.youtube.com/watch?v=otXHrlusl0A"),
    ("bio", "https://www.youtube.com/watch?v=rMhAhI98Xto"),
]
for ch, url in videos:
    try:
        q = urllib.parse.quote(url, safe="")
        req = urllib.request.Request(
            "https://www.youtube.com/oembed?url=" + q + "&format=json",
            headers={"User-Agent": "Mozilla/5.0"})
        d = json.loads(urllib.request.urlopen(req, timeout=20).read())
        print("%-8s LIVE  %r  by %s" % (ch, d["title"][:60], d["author_name"][:30]))
    except Exception as exc:  # noqa: BLE001
        print("%-8s NOT LIVE (%s): %s" % (ch, type(exc).__name__, exc))

repo = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
).stdout.strip()
out = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only",
                      "origin/main", "--", "factory/"],
                     capture_output=True, text=True).stdout.splitlines()
m = [f for f in out if "/content/m" in f and f.endswith(".json")]
b = [f for f in out if "/content_bio/b" in f and f.endswith(".json")]
c = [f for f in out if "content_chess/chess_part" in f and f.endswith(".json")]
print("origin banks: sci=%d  bio=%d  chess=%d" % (len(m), len(b), len(c)))
