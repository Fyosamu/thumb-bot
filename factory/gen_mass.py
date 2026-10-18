# -*- coding: utf-8 -*-
"""Build long-form scripts at scale from Wikipedia, one file per topic.

    python gen_mass.py sci --limit 12000        # -> content/m00001.json ...
    python gen_mass.py bio --limit 12000        # -> content_bio/b00001.json
    python gen_mass.py sci --force              # rebuild what is already there

The article is pulled with `exsectionformat=plain`, which returns clean
prose instead of wikitext - the earlier version stripped headings and refs
by regex and still leaked `=== Explanations ===` into the narration, which
the voice then read out loud.  Sentences are filtered again on the way out:
anything carrying markup characters, a citation, a URL or an ISBN is
dropped rather than repaired.

Every scene opens with a framing sentence that contains the topic itself,
so two articles that share a paragraph still render as different videos,
and the attribution line in the description keeps the CC BY-SA licence
happy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FACTORY = REPO / "factory"
API = "https://en.wikipedia.org/w/api.php"
UA = "chess-yt-bot/1.0 (script generation)"
CACHE = REPO / "wiki_cache"

CHANNELS = {
    "sci": {
        "folder": FACTORY / "content",
        "prefix": "m",
        "topics": REPO / "topics_sci.txt",
        "tags": ["philosophy", "psychology", "nihilism", "psychoanalysis",
                 "evolutionary psychology", "documentary", "deep thinking",
                 "mind", "explained"],
        "frames": [
            "The honest version of {topic} starts by giving up the comforting part.",
            "Strip {topic} of its poetry and the mechanism underneath is stranger.",
            "Evolution does not optimize for happiness — {topic} shows exactly where that breaks.",
            "What looks like free choice in {topic} is older than choice itself.",
            "Nobody designed the part of {topic} you experience — it was inherited.",
            "Every serious account of {topic} eventually collides with the question of who is deciding.",
            "Nihilism is not the conclusion of {topic} — it is the floor you stand on while examining it.",
            "The selfish-gene reading of {topic} makes it less romantic and far more precise.",
            "Freud is not dead; he is simply no longer allowed to be the whole answer.",
            "The feeling that {topic} means something is a chemical event with an evolutionary address.",
            "Nothing in {topic} was built for you — it was built for reproduction.",
            "The psychology underneath {topic} is simpler and older than the story on top.",
            "Behind {topic} sits an animal brain negotiating with a story it tells itself.",
            "The nihilist does not deny {topic} — he only refuses to flatter it.",
            "What culture calls destiny in {topic} is usually just selection pressure wearing a suit.",
            "The genes do not care about {topic}; they care about copies.",
            "Take away the meaning and {topic} still functions — that is the disturbing part.",
            "The unconscious does not argue with {topic}; it simply acts first.",
            "{topic} feels chosen. The evidence says it was installed.",
            "The bleak reading of {topic} is also the most testable one.",
            "Modern psychology keeps rediscovering what the pessimists said first about {topic}.",
            "The self that experiences {topic} is a committee, not a king.",
            "Reproduction explains more of {topic} than any philosophy dares to admit.",
            "Once you see {topic} as an adaptation, the mystery mostly evaporates.",
            "The story {topic} tells about itself is the last thing to be trusted.",
            "Meaning is not found in {topic} — it is manufactured for it.",
            "The cold light on {topic} leaves the facts intact and only the comfort removed.",
            "{topic} did not evolve to be understood — only to be survived.",
        ],
        "titles": [
            "{topic} — The Cold Version",
            "{topic} — What Science Actually Says",
            "The Dark Truth About {topic}",
            "{topic} — Meaning, Genes, And Nothing Else",
            "{topic} — Why You Feel It, And Who Decided",
            "The Nihilist Reading Of {topic}",
            "{topic} — Before Philosophy Got Polite",
            "{topic} — Survival, Reproduction, Illusion",
        ],
        "thumbs": ["NO COMFORT LEFT", "THE COLD VERSION", "GENES ALL THE WAY DOWN",
                   "WHO DECIDES", "MEANING IS CHEMISTRY", "OLDER THAN CHOICE",
                   "THE FLOOR DROPS", "SURVIVAL MACHINES", "INSTALLED, NOT CHOSEN",
                   "THE COMMITTEE SELF"],
    },
    "bio": {
        "folder": FACTORY / "content_bio",
        "prefix": "b",
        "topics": REPO / "topics_bio.txt",
        "tags": ["biography", "life story", "history", "documentary",
                 "inspirational", "learn", "biopic", "greatest lives"],
        "require_person": True,
        "frames": [
            "The life of {topic} begins far from where the story usually starts.",
            "{topic} was not born famous — the early years shaped everything that followed.",
            "To understand where {topic} ended up, start with where {topic} began.",
            "The road from the beginning to the peak of {topic} ran through years nobody filmed.",
            "Each stage of the life of {topic} made the next stage possible.",
            "The people who knew {topic} young describe someone already restless.",
            "What {topic} built in the middle years is what the name still stands for.",
            "By the time {topic} reached the defining moment, the preparation was decades old.",
            "The rise of {topic} was not an accident — in retrospect the pattern is plain.",
            "Setbacks came early for {topic}, and the response to them is the real story.",
            "The legacy of {topic} outlived the circumstances that produced it.",
            "Few lives travel as far as that of {topic}, and the distance is the point.",
            "The childhood of {topic} contains the adult in small print.",
            "Money, luck and timing all played their parts in the life of {topic} — in that order.",
            "The turning point in the life of {topic} looked like a failure at the time.",
            "Every biography of {topic} has to pass through the years that were quietly lost.",
            "The education of {topic} happened mostly outside any school.",
            "What {topic} wanted at the start and what {topic} got are not the same thing, and that gap is the story.",
            "The defining trait of {topic} was not talent — it was the refusal to stop.",
            "Those who met {topic} at the peak describe someone still running on the early hunger.",
            "The private years of {topic} explain the public decades better than any speech.",
            "The family {topic} came from matters more than the legends admit.",
            "The first real success of {topic} arrived later than anyone expected, and changed everything.",
            "The last chapter of {topic} was written long after the fame.",
            "The whole life of {topic} reads like a single decision repeated.",
            "Between the birth and the legend of {topic} lie the years that actually decide it.",
            "The reputation of {topic} was built in the middle, not at the edges.",
            "Somebody like {topic} should not have made it — that is exactly why the story survives.",
        ],
        "titles": [
            "The Life of {topic} — Who {topic} Really Was",
            "{topic} — Born, Raised, And What Came After",
            "How {topic} Got There — The Full Life Story",
            "{topic} — The Life, The Rise, And The Legacy",
            "From Nobody To History: The Story Of {topic}",
            "{topic} — The Journey That Made The Name",
            "Who Was {topic}? — The Whole Story",
            "{topic} — Beginning, Struggle, Peak",
        ],
        "thumbs": ["THE LIFE STORY", "WHO HE REALLY WAS", "FROM THE START",
                   "HOW IT HAPPENED", "THE WHOLE JOURNEY", "BORN, RAISED, ROSE",
                   "THE REAL LIFE", "WHAT IT TOOK"],
    },
}

STOCK = ["microscope close up", "water drop macro", "mountain aerial",
         "solar panels", "robot factory", "ant colony macro",
         "night city timelapse", "laboratory glassware", "storm clouds aerial",
         "paper documents close up", "old library", "archive boxes",
         "hands writing notes", "clock mechanism macro", "ocean waves aerial",
         "circuit board macro", "desert dunes aerial", "forest canopy aerial",
         "glass window rain", "industrial machinery", "train station crowd",
         "mountain ridge sunrise", "abstract light streaks", "smoke in dark"]

BAD = re.compile(r"[=<>{}\[\]|]|\bISBN\b|\bdoi\b|https?://|\bcitation needed\b|"
                 r"\bRetrieved\b|\bArchived\b|\bn\.d\.\b|\bpp?\.\s*\d|"
                 r"\bVol\.\s*\d|\bIbid\b|\bibid\b|\bQ\d{3,}\b")
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
# a life has a birth; a battle, a town or a treaty does not
PERSON = re.compile(
    r"\bborn\b|\bdied\b|\bb\.?\s*\d{3,4}\b|\bd\.?\s*\d{3,4}\b|"
    r"\((1[0-9]{3}|20[0-2][0-9])\s*[–-]\s*(1[0-9]{3}|20[0-2][0-9]|\d{3,4})\)",
    re.I)


def get_extract(title: str) -> str:
    """Plain-prose extract for one article, cached on disk."""
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / (hashlib.sha1(title.encode()).hexdigest() + ".txt")
    if dest.exists() and dest.stat().st_size > 400:
        return dest.read_text(encoding="utf-8")

    params = urllib.parse.urlencode({
        "action": "query", "prop": "extracts", "explaintext": "1",
        "exsectionformat": "plain", "titles": title, "redirects": "1",
        "format": "json"})
    for attempt in range(8):
        try:
            req = urllib.request.Request(API + "?" + params,
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.loads(r.read().decode("utf-8"))
            time.sleep(1.1)
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            print(f"    429, backing off", flush=True)
            time.sleep(18 + attempt * 6)
        except Exception as exc:                       # noqa: BLE001
            print(f"    retry {attempt + 1} ({type(exc).__name__})", flush=True)
            time.sleep(5 + attempt * 5)
    else:
        return ""

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        text = page.get("extract", "") or ""
        if text:
            dest.write_text(text, encoding="utf-8")
            return text
    return ""


def good(sentence: str) -> bool:
    s = sentence.strip()
    if not (12 <= len(s.split()) <= 46):
        return False
    if BAD.search(s):
        return False
    if s.count('"') % 2:                                # dangling quote
        return False
    if not s.endswith((".", "!", "?")):
        return False
    if re.match(r"^(He|She|It|They|His|Her|Their)\b", s) and len(s.split()) < 16:
        return False                                    # fragment without an antecedent
    return True


def body_sentences(text: str) -> list[str]:
    out, seen = [], set()
    for para in text.split("\n"):
        para = para.strip()
        if not para or len(para) < 120:
            continue
        for raw in SENT.split(para):
            s = raw.strip()
            if good(s) and s not in seen:
                seen.add(s)
                out.append(s)
    return out


def build(topic: str, cfg: dict, n: int, idx: int, force: bool) -> bool:
    slug = f"{cfg['prefix']}{n:05d}"
    dest = cfg["folder"] / f"{slug}.json"
    if dest.exists() and not force:
        return False

    text = get_extract(topic)
    if len(text) < 1200:
        return False
    # the biography topic scrape drags in list pages, towns, battles and
    # treaties - the article itself says whether it is about a person
    if cfg.get("require_person") and not PERSON.search(text[:900]):
        return False
    pool = body_sentences(text)
    if len(pool) < 26:
        return False

    hi = min(len(pool), 34)
    scenes: list[dict] = []
    words = 0
    cursor = 0
    frame_i = idx % len(cfg["frames"])
    while len(scenes) < hi and cursor + 1 < len(pool):
        frame = cfg["frames"][frame_i].format(topic=topic)
        frame_i = (frame_i + 1) % len(cfg["frames"])
        take = [pool[cursor], pool[cursor + 1]]
        cursor += 2
        narr = frame + " " + " ".join(take)
        if words + len(narr.split()) > 2250:
            break
        scenes.append({"stock": STOCK[(idx + len(scenes)) % len(STOCK)],
                       "narration": narr})
        words += len(narr.split())

    if words < 1700 or len(scenes) < 24:
        return False

    title = cfg["titles"][idx % len(cfg["titles"])].format(topic=topic)
    doc = {
        "slug": slug,
        "topic": topic,
        "title": title,
        "orientation": "landscape",
        "voice": "en-US-AvaMultilingualNeural",
        "thumb_text": cfg["thumbs"][idx % len(cfg["thumbs"])],
        "thumb_stock": STOCK[idx % len(STOCK)],
        "description": (scenes[0]["narration"] + "\n\n" +
                        scenes[-1]["narration"] +
                        "\n\nSource: Wikipedia (CC BY-SA 4.0). "
                        "Made with AI assistance.\n\n" +
                        " ".join("#" + t.replace(" ", "") for t in
                                 cfg["tags"][:3]) + "\n")[:4900],
        "tags": list(dict.fromkeys([topic.lower()] + cfg["tags"]))[:40],
        "scenes": scenes,
        "_words": words,
    }
    dest.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"  {slug} {words:5d}w {len(scenes):2d}sc  {title[:58]}", flush=True)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=list(CHANNELS))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--minutes", type=float, default=0,
                    help="stop after this many minutes; CI runs are budgeted")
    args = ap.parse_args()
    deadline = time.time() + args.minutes * 60 if args.minutes else 0

    cfg = CHANNELS[args.which]
    cfg["folder"].mkdir(parents=True, exist_ok=True)
    topics = cfg["topics"].read_text(encoding="utf-8").splitlines()
    topics = [t.strip() for t in topics if t.strip()]
    if args.limit:
        topics = topics[:args.limit]

    # resume where the last run stopped instead of re-numbering from zero,
    # and never spend a fetch on a topic that already has its script
    taken: set[str] = set()
    highest = -1
    for old in cfg["folder"].glob(f"{cfg['prefix']}*.json"):
        stem = old.stem
        if "_short" in stem or not stem[len(cfg["prefix"]):].isdigit():
            continue
        highest = max(highest, int(stem[len(cfg["prefix"]):]))
        try:
            used = json.loads(old.read_text(encoding="utf-8")).get("topic")
        except Exception:                               # noqa: BLE001
            used = None
        if used:
            taken.add(used)
    n = highest + 1
    print(f"resuming at {cfg['prefix']}{n:05d}, "
          f"{len(taken)} topics already covered", flush=True)

    made = 0
    for idx, topic in enumerate(topics):
        if deadline and time.time() > deadline:
            print("time budget reached", flush=True)
            break
        if topic in taken:
            continue
        try:
            if build(topic, cfg, n, idx, args.force):
                made += 1
                n += 1
        except Exception as exc:                       # noqa: BLE001
            print(f"  skip {topic!r}: {type(exc).__name__}", flush=True)
        if n >= 10000:
            break
    print(f"\n{made} scripts written into {cfg['folder'].name}/", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
