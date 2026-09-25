# -*- coding: utf-8 -*-
"""Photo library for the bots.

  * Pexels  -> chess / science / b-roll photos (free, unlimited, no captcha)
  * Wikipedia -> portraits for the biography channel (free, stable, no key)

Everything is cached as URLs in bot/photo_lib.json so the repo never carries
big binaries: a GitHub Actions run picks an id, downloads one image and uses it.
"""

import json
import os
import random
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "photo_lib.json")

PEXELS_KEY = os.environ.get(
    "PEXELS_KEY", "DlTa4XKMzuGCvBy2bTTfvul2JP18DPM1LXYs4wHyHhRnrLqfJ9i55sm8")
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}

# queries used by the different channels
QUERIES = {
    "chess_master": [
        "chess grandmaster", "chess player thinking", "chess tournament",
        "chess match players", "chess pieces board", "chess clock",
        "professional chess game", "chess club", "chess championship", "two men playing chess",
    ],
    "science": [
        "science laboratory", "microscope research", "space galaxy", "dna molecule",
        "brain neuroscience", "robot technology", "volcano eruption", "ocean deep",
        "solar system", "chemistry experiment", "physics experiment", "astronomy telescope",
        "human anatomy", "climate earth", "quantum computer", "electricity plasma",
        "fossil dinosaur", "cell microscopy", "black hole", "wildlife macro",
    ],
    "broll": [
        "city timelapse", "forest fog", "desert dunes", "storm clouds",
        "mountain snow", "river aerial", "night sky stars", "fire flames",
        "old books library", "clock time", "hands writing", "typewriter",
    ],
    "biography": [
        "vintage portrait", "old photograph man", "historic archive",
        "museum painting portrait", "antique desk writing",
    ],
}


def _get(url, headers=None, timeout=60):
    h = dict(UA)
    if headers:
        h.update(headers)
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout).read()


def load_lib():
    if os.path.exists(LIB):
        with open(LIB, encoding="utf-8") as f:
            return json.load(f)
    return {k: [] for k in QUERIES}


def save_lib(lib):
    os.makedirs(os.path.dirname(LIB), exist_ok=True)
    with open(LIB, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False)


def search_pexels(query, landscape=True, per_page=40, page=None):
    """Live Pexels search - use it when the photo must MATCH the video topic."""
    import random as _rnd
    url = ("https://api.pexels.com/v1/search?query=%s&per_page=%d&page=%d"
           % (urllib.parse.quote(query), per_page, page or _rnd.randint(1, 6)))
    data = json.loads(_get(url, {"Authorization": PEXELS_KEY}))
    out = []
    for p in data.get("photos", []):
        if landscape and p["width"] < p["height"]:
            continue
        out.append({"id": p["id"], "w": p["width"], "h": p["height"],
                    "url": p["src"].get("large2x") or p["src"].get("original"),
                    "q": query, "alt": (p.get("alt") or "")[:120]})
    return out


def get_photo_query(query, out, landscape=True, queries=None, required=None,
                    forbidden=None):
    """Download the topic-relevant Pexels photo.

    Ranking = query-word overlap + bonus for the action we want to show
    (yell / scream / open mouth ...) - penalty for irrelevant props.
    """
    words = [w for w in "".join(c if c.isalpha() or c.isspace() else " "
                                for c in query.lower()).split() if len(w) > 2]
    required = [r.lower() for r in (required or [])]
    forbidden = [f.lower() for f in (forbidden or [])]
    tries = queries or [query, "%s close up" % query, "%s portrait" % query,
                        "%s face" % query]
    cands = []
    seen = set()
    for q in tries:
        try:
            found = search_pexels(q, landscape=landscape)
        except Exception as e:                          # noqa: BLE001
            print("[pexels] %r: %s" % (q, e))
            continue
        time.sleep(1)
        for ent in found:
            if ent["id"] in seen:
                continue
            seen.add(ent["id"])
            cands.append(ent)
    if not cands:
        raise RuntimeError("no Pexels photo for %r" % query)

    def score(ent):
        alt = (ent.get("alt") or "").lower()
        if not alt:
            return -5
        s = sum(2 for w in words if w in alt)
        s += sum(4 for r in required if r in alt)
        s -= sum(8 for f in forbidden if f in alt)
        if any(k in alt for k in ("close-up", "close up", "closeup")):
            s += 2
        if any(k in alt for k in ("yelling", "screaming", "shouting", "scream",
                                  "yell", "shout", "open mouth")):
            s += 4
        return s

    cands.sort(key=score, reverse=True)
    best = cands[0]
    download(best, out)
    print("[pexels] %r score=%d -> %s" % (query, score(best),
                                           best.get("alt") or best["id"]))
    return best, out


def fetch_pexels(query, per_page=80, pages=5, existing=None):
    out = []
    seen = existing or set()
    for page in range(1, pages + 1):
        url = ("https://api.pexels.com/v1/search?query=%s&per_page=%d&page=%d"
               % (urllib.parse.quote(query), per_page, page))
        try:
            data = json.loads(_get(url, {"Authorization": PEXELS_KEY}))
        except Exception as e:                      # noqa: BLE001
            print("[pexels] %s p%d: %s" % (query, page, e))
            break
        for p in data.get("photos", []):
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            out.append({"id": p["id"], "w": p["width"], "h": p["height"],
                        "url": p["src"].get("large2x") or p["src"].get("original"),
                        "q": query})
        if not data.get("next_page"):
            break
    return out


def build(category, pages=5):
    """Top up photo_lib.json for one category."""
    lib = load_lib()
    for q in QUERIES[category]:
        have = {e["id"] for e in lib.get(category, [])}
        new = fetch_pexels(q, pages=pages, existing=have)
        lib.setdefault(category, []).extend(new)
        print("[pexels] %-14s +%-4d total=%d" % (q, len(new), len(lib[category])))
    save_lib(lib)
    return len(lib.get(category, []))


def pick(category, min_landscape=True):
    """Random entry for a category (falls back to any entry)."""
    lib = load_lib()
    pool = lib.get(category) or []
    if min_landscape:
        wide = [e for e in pool if e["w"] >= e["h"]]
        if wide:
            pool = wide
    if not pool:
        raise RuntimeError("photo_lib empty for %r - run photo_lib.build()" % category)
    return random.choice(pool)


def download(entry, out, timeout=90):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    data = _get(entry["url"], timeout=timeout)
    with open(out, "wb") as f:
        f.write(data)
    return out


def get_photo(category, out, **kw):
    return download(pick(category, **kw), out)


# ------------------------------------------------------------------ biography portraits
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/%s"


def wiki_portrait(title, lang="en"):
    """Portrait of a biography subject straight from Wikipedia (no key, no captcha)."""
    url = ("https://%s.wikipedia.org/api/rest_v1/page/summary/%s"
           % (lang, urllib.parse.quote(title.replace(" ", "_"))))
    d = json.loads(_get(url))
    thumb = (d.get("thumbnail") or d.get("originalimage") or {})
    src = thumb.get("source")
    if not src:
        return None
    if thumb.get("width", 0) < 400 and d.get("originalimage", {}).get("source"):
        src = d["originalimage"]["source"]
    return {"title": d.get("title", title), "url": src,
            "desc": (d.get("description") or "")[:120]}


def get_portrait(title, out, lang="en"):
    info = wiki_portrait(title, lang)
    if not info:
        raise RuntimeError("no portrait for %r" % title)
    download(info, out)
    info["file"] = out
    return info


# --------------------------------------------------- Wikimedia Commons (free photos)
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

GRANDMASTERS = [
    "Magnus Carlsen", "Garry Kasparov", "Hikaru Nakamura", "Bobby Fischer",
    "Mikhail Tal", "Viswanathan Anand", "Vladimir Kramnik", "Anatoly Karpov",
    "Fabiano Caruana", "Ding Liren", "Levon Aronian", "Ian Nepomniachtchi",
    "Maxime Vachier-Lagrave", "Sergey Karjakin", "Judit Polgar", "Hou Yifan",
    "Boris Spassky", "Mikhail Botvinnik", "José Raúl Capablanca", "Emanuel Lasker",
    "Alexander Alekhine", "Paul Morphy", "Wesley So", "Alireza Firouzja",
    "Arjun Erigaisi", "R. Praggnanandhaa", "Vincent Keymer", "Dommaraju Gukesh",
]


def commons_search(query, limit=30, width=1600):
    """Free-licensed photos from Wikimedia Commons (no key, no captcha)."""
    url = ("%s?action=query&format=json&generator=search&gsrsearch=%s"
           "&gsrnamespace=6&gsrlimit=%d&prop=imageinfo&iiprop=url|size|mime"
           "&iiurlwidth=%d" % (COMMONS_API, urllib.parse.quote(query), limit, width))
    d = json.loads(_get(url))
    out = []
    for page in (d.get("query", {}).get("pages") or {}).values():
        ii = (page.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl"):
            continue
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        out.append({"id": page["pageid"], "w": ii.get("thumbwidth", 0),
                    "h": ii.get("thumbheight", 0), "url": ii["thumburl"],
                    "title": page.get("title", ""), "q": query})
    return out


def build_grandmasters(per_player=20):
    """Photo pool of top players actually sitting at a board."""
    lib = load_lib()
    lib.setdefault("grandmaster", [])
    have = {e["id"] for e in lib["grandmaster"]}
    done = {}
    for e in lib["grandmaster"]:
        p = e.get("player")
        if p:
            done[p] = done.get(p, 0) + 1
    for name in GRANDMASTERS:
        if done.get(name, 0) >= 15:
            print("[commons] %-24s already %d" % (name, done[name]))
            continue
        n = 0
        for q in ("%s chess" % name, "%s game" % name, "%s tournament" % name):
            found = []
            for attempt in range(4):
                try:
                    found = commons_search(q, per_player)
                    break
                except Exception as e:                 # noqa: BLE001
                    print("[commons] %s: %s (retry %d)" % (q, e, attempt + 1))
                    time.sleep(6 + attempt * 6)
            time.sleep(2.5)
            for e in found:
                if e["id"] in have:
                    continue
                have.add(e["id"])
                e["player"] = name
                lib["grandmaster"].append(e)
                n += 1
            if n:
                done[name] = done.get(name, 0) + n
        print("[commons] %-24s +%d total=%d" % (name, n, len(lib["grandmaster"])))
    save_lib(lib)
    return len(lib["grandmaster"])


def pick_player(name=None):
    """Random photo of a grandmaster (optionally a specific one)."""
    lib = load_lib()
    pool = [e for e in lib.get("grandmaster", [])
            if (name is None or e.get("player", "").lower() == name.lower())
            and e["w"] >= e["h"]]
    if not pool:
        raise RuntimeError("no grandmaster photo for %r" % name)
    return random.choice(pool)


if __name__ == "__main__":
    import sys
    cat = sys.argv[1] if len(sys.argv) > 1 else "chess_master"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    print("total:", build(cat, pages))
