# -*- coding: utf-8 -*-
"""Fetch original-size images from Pinterest (no login) for thumbnail work.

    python bot/pin_fetch.py "chess puzzle" out_dir 12
"""
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def _opener(query):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept-Language", "en-US,en;q=0.9")]
    search = "https://www.pinterest.com/search/pins/?q=" + urllib.parse.quote(query)
    op.open(search, timeout=40).read()
    tok = next((c.value for c in cj if c.name == "csrftoken"), None)
    return op, tok, search


def search(query, page_size=30, log=print):
    """Return a list of original-size pin image URLs."""
    op, tok, search_url = _opener(query)
    data = {"options": {"query": query, "scope": "pins", "page_size": page_size,
                        "accessibility": {"prefers_reduced_motion": False}},
            "context": {"app_version": "2026.9.26.1", "client_code": 11,
                        "browser_locale": "en-US", "csrf_token": tok or ""}}
    url = ("https://www.pinterest.com/resource/BaseSearchResource/get/"
           "?source_id=%s&_=%d&data=%s"
           % (uuid.uuid4(), int(time.time() * 1000),
              urllib.parse.quote(json.dumps(data))))
    hdr = {"User-Agent": UA,
           "Accept": "application/json, text/javascript, */*; q=0.01",
           "X-Requested-With": "XMLHttpRequest",
           "X-Pinterest-AppState": "active",
           "Referer": search_url,
           "Content-Type": "application/json"}
    if tok:
        hdr["X-CSRFToken"] = tok
    raw = op.open(urllib.request.Request(url, data=json.dumps(data).encode(),
                                         headers=hdr), timeout=45).read()
    js = json.loads(raw)
    res = (js.get("resource_response") or {}).get("data") or {}
    out = []
    for r in (res.get("results") or []):
        imgs = r.get("images") or {}
        for key in ("original", "orig", "736x", "564x"):
            v = imgs.get(key) or {}
            if v.get("url"):
                out.append(v["url"])
                break
    if not out:
        txt = raw.decode("utf-8", "ignore")
        for m in re.finditer(
                r"https://i\.pinimg\.com/(?:originals|736x|564x)/"
                r"[^\"'\\\s&]+?\.(?:jpg|jpeg|png|webp)", txt):
            if m.group(0) not in out:
                out.append(m.group(0))
    log("[pin] %r -> %d urls" % (query, len(out)))
    return out


def download(url, dest, log=print):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    data = urllib.request.urlopen(req, timeout=60).read()
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    log("[pin] saved %s (%d KB)" % (os.path.basename(dest), len(data) // 1024))
    return dest


def fetch(query, out_dir, limit=12, log=print):
    urls = search(query, log=log)
    saved = []
    for i, u in enumerate(urls, 1):
        if len(saved) >= limit:
            break
        ext = os.path.splitext(u.split("?")[0])[1] or ".jpg"
        try:
            saved.append(download(u, os.path.join(out_dir, "pin%02d%s" % (i, ext)), log))
        except Exception as e:
            log("[pin] skip %s: %s" % (u.rsplit("/", 1)[-1], e))
    return saved


if __name__ == "__main__":
    q = sys.argv[1]
    out = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    files = fetch(q, out, n)
    print("downloaded %d -> %s" % (len(files), out))
