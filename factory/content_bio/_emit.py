import json
import os

D = os.path.dirname(os.path.abspath(__file__))

BANNED = {"concept", "idea", "background", "texture", "abstract", "science", "psychology", "portrait"}


def _words(s):
    return len(s.split())


def emit(name, data, kind="long"):
    path = os.path.join(D, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    scenes = data["scenes"]
    counts = [_words(s["narration"]) for s in scenes]
    total = sum(counts)
    problems = []

    if kind == "long":
        if not 28 <= len(scenes) <= 36:
            problems.append("scene count %d" % len(scenes))
        if not 1400 <= total <= 2700:
            problems.append("total words %d" % total)
        if not 1700 <= total <= 2200:
            problems.append("target words %d" % total)
        for i, c in enumerate(counts, 1):
            if not 45 <= c <= 90:
                problems.append("scene %d = %d words" % (i, c))
    else:
        if not 5 <= len(scenes) <= 7:
            problems.append("scene count %d" % len(scenes))
        if not 95 <= total <= 140:
            problems.append("total words %d" % total)

    stocks = [s["stock"] for s in scenes]
    stocks.append(data["thumb_stock"])
    for st in stocks:
        n = len(st.split())
        if not 2 <= n <= 4:
            problems.append("stock '%s' = %d words" % (st, n))
        for w in st.lower().replace("-", " ").split():
            if w in BANNED:
                problems.append("stock '%s' has banned word '%s'" % (st, w))
    for st in set(stocks):
        if stocks.count(st) > 1:
            problems.append("stock '%s' repeated" % st)

    print("%-24s scenes=%2d words=%4d  %s" % (name, len(scenes), total,
                                              "OK" if not problems else "; ".join(problems)))
    if problems:
        print("     per-scene:", counts)
    return problems
