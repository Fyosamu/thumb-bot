# -*- coding: utf-8 -*-
"""Personal-development rip-translate robot (channel 4).

Every day, forever:
  discover a fresh Persian personal-development video
  -> download its audio + thumbnail
  -> pull the transcript (auto-subs first, whisper fallback)
  -> strip every personal trace (telegram, instagram, phones, links, promos)
  -> translate sentence-by-sentence to English
  -> build our own copyright-free script (stock scenes + captions + TTS voice)
  -> render through the factory, thumbnail = the source creator's image with
     the Persian text covered and an English title
  -> upload through upload.py (channel 4, daily cap 1, its own manifest)

    python robot.py                     # normal daily run
    python robot.py --video <url>       # force one specific source video
    python robot.py --no-upload         # build + render only
    python robot.py --channel 47        # run as multichan channel 47
                                        # (category queries + voice from
                                        # projects/multichan/channels.json)

Token: repo secret PD_TOKEN_JSON -> env YT4_TOKEN_JSON.  Without it the
robot still discovers/translates/renders and just skips the upload line,
so the pipeline is never cold when the token arrives.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FACTORY = REPO / "factory"
STATE_FILE = HERE / "state" / "processed_pd.json"
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))

sys.path.insert(0, str(FACTORY))
import channels  # noqa: E402

PROF = channels.profile("4")
CONTENT, OUTDIR = PROF["content"], PROF["out"]
CHANNEL = "4"                       # overridden by --channel / PD_CHANNEL
QUERIES = CONFIG["queries"]         # per-channel from the multichan registry
VOICE = CONFIG["voice"]             # rotating edge-tts voice per channel


def _registry(cid: str) -> dict | None:
    """projects/multichan/channels.json entry for this channel, if it is one
    of the 100 category channels - then discovery searches ITS category's
    Persian queries and TTS speaks with ITS voice."""
    p = HERE.parent / "multichan" / "channels.json"
    if not p.exists():
        return None
    for e in json.loads(p.read_text(encoding="utf-8")).get("channels", []):
        if str(e["id"]) == str(cid):
            return e
    return None


# ---------------------------------------------------------------- state ----
def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                          encoding="utf-8")


# ------------------------------------------------------------ discover ----
def ytdlp(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "yt_dlp", *args]
    cookies = os.environ.get("COOKIES_FILE", "").strip()
    if cookies and Path(cookies).exists() and "--cookies" not in args:
        cmd += ["--cookies", cookies]
    return subprocess.run(cmd, capture_output=True, text=True, check=check,
                          encoding="utf-8", errors="replace")


def _aparat_get(url: str, tries: int = 4, timeout: int = 20) -> object | None:
    """aparat's edge answers 504 in bursts (2026-10-20: homepage, search,
    show API - everything, for hours) - retry with backoff instead of
    collapsing the whole discovery pass into '0 candidates'."""
    import requests
    delay = 1.5
    for i in range(tries):
        try:
            r = requests.get(url, timeout=timeout,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.ok and r.content:
                return r
            print(f"[pdrip] aparat http {r.status_code} "
                  f"(try {i + 1}/{tries})")
        except Exception as exc:                # noqa: BLE001 - retry
            print(f"[pdrip] aparat {type(exc).__name__} "
                  f"(try {i + 1}/{tries})")
        time.sleep(delay)
        delay *= 2
    return None


def _aparat_slugs() -> list[str]:
    """Freshest video hashes from aparat's sitemaps - the safety net for
    when the search API itself is down."""
    slugs: list[str] = []
    for n in (1, 2, 3, 4, 5):
        r = _aparat_get(f"https://www.aparat.com/sitemap_{n}.xml",
                        tries=2, timeout=25)
        if r is None:
            continue
        found = re.findall(
            r"<loc>https://www\.aparat\.com/v/([A-Za-z0-9]+)</loc>", r.text)
        for s in found:
            if s not in slugs:
                slugs.append(s)
    print(f"[pdrip] aparat sitemaps: {len(slugs)} slugs")
    return slugs


STRONG = ("توسعه فردی", "انگیزش", "روانشناسی", "موفقیت", "عادت", "هدف",
          "پیشرفت", "خودسازی", "اعتماد به نفس", "تمرکز", "مدیریت زمان",
          "شادی", "یادگیری", "ذهن", "ذهنیت", "آگاهی", "رفتار", "هیجان")
WEAK = ("زندگی", "قدرت", "ایمان", "امید", "مغز", "مثبت", "درس")


def _aparat_show(video_hash: str) -> dict | None:
    r = _aparat_get(
        "https://www.aparat.com/api/fa/v1/video/video/show/videohash/"
        + video_hash, tries=2, timeout=12)
    if r is not None:
        try:
            return (r.json().get("data") or {}).get("attributes") or None
        except Exception:                       # noqa: BLE001 - drop it
            pass
    return None


def _aparat_search(query: str) -> list[dict]:
    """Aparat's own search API - real topical results, json:api envelope
    (videos live in .included[].attributes)."""
    import urllib.parse

    import requests
    # zero-width non-joiner (نیم‌فاصله) makes the endpoint answer 400
    query = " ".join(query.replace("\u200c", " ").split())
    url = ("https://www.aparat.com/api/fa/v1/video/video/search/text/"
           + urllib.parse.quote(query) + "/?type_search=search")
    r = _aparat_get(url, tries=3, timeout=18)
    if r is None:
        return []
    try:
        return [(a.get("attributes") or {})
                for a in (r.json().get("included") or [])]
    except Exception as exc:                # noqa: BLE001 - next query
        print(f"[pdrip] aparat search {query!r}: {type(exc).__name__}")
        return []


FAILED_TTL = 12 * 3600   # seconds - an outage must not poison later waves:
                         # aparat 504s at 13:00, recovers by 16:00, and the
                         # rescue wave must still be allowed to retry the
                         # exact same candidates


def _fail(state: dict, url: str, reason: str) -> None:
    state.setdefault("failed", {})[url] = {"reason": reason,
                                           "at": time.time()}


def _failed_recent(state: dict, url: str) -> bool:
    mark = state.get("failed", {}).get(url)
    if not isinstance(mark, dict):
        return False          # legacy string marks are already expired
    return time.time() - float(mark.get("at", 0)) < FAILED_TTL


def discover_aparat(state: dict) -> list[dict]:
    """First-choice source: an Iranian platform with no bot-checks at all,
    exactly the Iranian personal-development shelf the owner asked for.
    Discovery = aparat search API (topical) -> topic/quality filters ->
    show API for the pre-signed CDN files."""
    if not CONFIG.get("aparat", True):
        return []
    seen, failed = state["processed"], state.get("failed", {})
    want = CONFIG.get("aparat_results", 6)

    pool: list[dict] = []
    for q in QUERIES:
        for a in _aparat_search(q):
            uid = a.get("uid") or ""
            if uid and not any(c.get("uid") == uid for c in pool):
                pool.append(a)
        time.sleep(0.3)

    if not pool:
        # search dead - random newest videos, so topicality needs the
        # keyword score here and only here
        print("[pdrip] aparat search empty - sitemap fallback probing")
        slugs = _aparat_slugs()
        with ThreadPoolExecutor(max_workers=10) as ex:
            for a in ex.map(_aparat_show, slugs[:288]):
                if a:
                    a["_random"] = True
                    pool.append(a)

    # sweet spot ~7.5 min: real talk length, and every minute of source
    # is a minute of whisper + translate + render, so shorter = faster
    pool.sort(key=lambda a: abs(int(a.get("duration") or 0) - 450))
    cands: list[dict] = []
    for a in pool:
        if len(cands) >= want:
            break
        dur = int(a.get("duration") or 0)
        title = a.get("title") or ""
        desc = (a.get("description") or "")[:300]
        text = title + " " + desc
        if not (CONFIG["min_duration"] <= dur <= CONFIG["max_duration"]):
            continue
        if any(w in text for w in CONFIG["skip_words"]):
            continue
        if a.get("_random"):
            score = sum(2 for k in STRONG if k in text) + \
                sum(1 for k in WEAK if k in text)
            if score < 2:
                continue
        uid = a.get("uid") or ""
        url = f"https://www.aparat.com/v/{uid}"
        if url in seen or _failed_recent(state, url):
            continue
        full = a if a.get("file_link_all") else (_aparat_show(uid) or {})
        files = [(f.get("profile") or "",
                  (f.get("urls") or [""])[0])
                 for f in (full.get("file_link_all") or [])
                 if f.get("urls")]
        if not files:
            continue
        cands.append({
            "url": url, "id": uid, "source": "aparat",
            "title": title, "duration": dur,
            "thumbnail": full.get("big_poster") or a.get("big_poster") or "",
            "files": files,
            "_description": desc,
        })
    print(f"[pdrip] aparat: {len(pool)} in pool -> {len(cands)} candidates")
    return cands


def discover(state: dict, force_url: str | None) -> list[dict]:
    seen = state["processed"]
    failed = state.get("failed", {})
    cands: list[dict] = []

    if force_url:
        r = ytdlp(["-J", "--skip-download", force_url], check=False)
        if r.returncode != 0:
            print(f"[pdrip] cannot read {force_url}: {r.stderr[-300:]}")
            return []
        return [json.loads(r.stdout)]

    aparat_cands = discover_aparat(state)

    for q in QUERIES:
        r = ytdlp(["--flat-playlist", "-J",
                   f"ytsearch{CONFIG['search_results']}:{q}"], check=False)
        if r.returncode != 0:
            print(f"[pdrip] search failed for {q!r}")
            continue
        try:
            entries = json.loads(r.stdout).get("entries") or []
        except json.JSONDecodeError:
            continue
        for e in entries:
            if not e or not e.get("id"):
                continue
            url = e.get("url") or f"https://youtu.be/{e['id']}"
            dur = e.get("duration") or 0
            title = e.get("title") or ""
            if not (CONFIG["min_duration"] <= dur <= CONFIG["max_duration"]):
                continue
            # a real content failure (no transcript / too short) blocks a
            # URL for FAILED_TTL seconds only - a 13:00 outage wave must
            # never poison the 19:00 rescue wave
            if url in seen or _failed_recent(state, url):
                continue
            if any(w in title for w in CONFIG["skip_words"]):
                continue
            cands.append({"url": url, "id": e["id"], "title": title,
                          "duration": dur, "channel": e.get("channel") or ""})
        time.sleep(0.5)

    cands = aparat_cands + cands
    if not cands:
        print("[pdrip] no fresh candidate (bank of sources exhausted for now)")
        return []
    print(f"[pdrip] {len(aparat_cands)} aparat + "
          f"{len(cands) - len(aparat_cands)} youtube candidates, first: "
          f"{cands[0].get('title', '')[:60]}")
    return cands


# ----------------------------------------------------------- download ----
# YouTube bot-checks datacenter IPs on the default web client; the tv /
# android / ios clients speak different APIs and sail through.  Try each,
# fall back to default, before giving up on a candidate.
CLIENT_ROTATION = [
    ["--extractor-args", "youtube:player_client=tv_simply"],
    ["--extractor-args", "youtube:player_client=web_embedded"],
    ["--extractor-args", "youtube:player_client=android"],
    ["--extractor-args", "youtube:player_client=mweb"],
    ["--extractor-args", "youtube:player_client=ios"],
    ["--extractor-args", "youtube:player_client=tv"],
    [],
]


def download(url: str, work: Path, source: str = "youtube"
             ) -> tuple[Path | None, Path | None]:
    work.mkdir(parents=True, exist_ok=True)
    subs = ",".join(CONFIG["sub_langs"])
    # aparat has no player wall - one plain call; youtube needs clients.
    # audio-only selectors (ba[ext=m4a]) died with the SABR experiment -
    # clients skip formats without a URL, so the whole selector misses.
    # progressive b/ba/best always resolves (it is what worked when every
    # client rotation failed); the output never uses source video anyway.
    if source == "aparat":
        attempts = [([], "ba[ext=m4a]/ba"), ([], "b/ba/best")]
    else:
        attempts = [(e, "ba[ext=m4a]/ba") for e in CLIENT_ROTATION] + \
                   [(e, "b/ba/best") for e in CLIENT_ROTATION]
    for extra, fmt in attempts:
        r = ytdlp([
            *extra,
            "-f", fmt,
            "-o", str(work / "source.%(ext)s"),
            "--write-info-json",
            "--write-auto-subs", "--write-subs",
            "--sub-langs", subs,
            "--sub-format", "json3/best",
            "--write-thumbnail", "--convert-thumbnails", "jpg",
            "--retries", "3",
            url,
        ], check=False)
        if r.returncode == 0:
            if extra:
                print(f"[pdrip] downloaded via {extra[-1].split('=')[-1]} "
                      f"({fmt})")
            break
        print(f"[pdrip] download attempt "
              f"{(extra[-1].split('=')[-1] if extra else 'default')} "
              f"failed ({fmt})")
    else:
        print(f"[pdrip] all clients failed for {url}")
        return None, None
    audio = next((p for p in work.glob("source.*")
                  if p.suffix not in (".json", ".jpg", ".vtt", ".json3")), None)
    thumb = next(iter(work.glob("source*.jpg")), None)
    return audio, thumb


def fetch_thumb(video_id: str, work: Path) -> Path | None:
    """The source creator's thumbnail, straight from the image CDN
    (no player, no bot-check).  maxres -> sd -> default, first hit wins."""
    import requests
    dest = work / "source_thumb.jpg"
    for name in ("maxresdefault", "sddefault", "hqdefault"):
        url = f"https://i.ytimg.com/vi/{video_id}/{name}.jpg"
        try:
            r = requests.get(url, timeout=15)
            if r.ok and len(r.content) > 5000:
                dest.write_bytes(r.content)
                return dest
        except Exception:                   # noqa: BLE001 - next size
            continue
    return None


def fetch_aparat_poster(info: dict, work: Path) -> Path | None:
    """The aparat creator's own thumbnail from the CDN, straight from the
    show API (big_poster) - no bot-check there either."""
    import requests
    src = info.get("thumbnail") or ""
    if not src:
        return None
    try:
        r = requests.get(src, timeout=20)
        if r.ok and len(r.content) > 5000:
            dest = work / "source_thumb.jpg"
            dest.write_bytes(r.content)
            return dest
    except Exception:                       # noqa: BLE001 - keep factory one
        pass
    return None


def download_aparat(info: dict, work: Path) -> Path | None:
    """Direct pre-signed CDN files from the show API.  Whisper only needs
    the audio track, so the smallest usable profile wins (144p first)."""
    import requests
    pairs = sorted(info.get("files") or [],
                   key=lambda p: int(re.sub(r"\D", "", p[0]) or "999"))
    for profile, url in pairs[:3]:
        if not url:
            continue
        try:
            with requests.get(url, timeout=180, stream=True) as r:
                if not r.ok:
                    print(f"[pdrip] aparat {profile}: HTTP {r.status_code}")
                    continue
                dest = work / "source.mp4"
                size = 0
                with open(dest, "wb") as fh:
                    for chunk in r.iter_content(1 << 16):
                        fh.write(chunk)
                        size += len(chunk)
            if size > 100_000:
                print(f"[pdrip] aparat source via {profile} "
                      f"({size // 1024} KB)")
                return dest
        except Exception as exc:            # noqa: BLE001 - next profile
            print(f"[pdrip] aparat {profile}: {type(exc).__name__}")
    return None


def _proxy_audio(video_id: str, work: Path) -> Path | None:
    """Player walled but a Piped instance alive? Its audioStreams are
    proxied through the instance - grab one so whisper has input."""
    import requests
    for base in CONFIG.get("caption_proxies", []):
        host = base.split("//")[1]
        try:
            r = requests.get(f"{base}/streams/{video_id}", timeout=20)
            if not r.ok:
                continue
            streams = (r.json().get("audioStreams") or [])
            streams = sorted(streams, key=lambda s: (
                0 if str(s.get("format", "")).lower() in ("m4a", "mp4") else 1,
                -(s.get("bitrate") or 0)))
            for s in streams[:2]:
                dest = work / f"source.proxy.{s.get('format') or 'm4a'}"
                with requests.get(s["url"], timeout=120, stream=True) as ar:
                    if not ar.ok:
                        continue
                    size = 0
                    with open(dest, "wb") as fh:
                        for chunk in ar.iter_content(1 << 16):
                            fh.write(chunk)
                            size += len(chunk)
                if size > 100_000:
                    print(f"[pdrip] audio via {host} ({size // 1024} KB, "
                          "whisper now possible)")
                    return dest
        except Exception as exc:            # noqa: BLE001 - next instance
            print(f"[pdrip] audio-proxy {host}: {type(exc).__name__}")
    return None


# ---------------------------------------------------------- transcript ----
def _parse_vtt_text(text: str) -> list[str]:
    lines_out, prev = [], ""
    for raw in text.splitlines():
        s = raw.strip()
        if (not s or "-->" in s or s.startswith(("WEBVTT", "Kind:", "Language:",
                                                  "NOTE")) or s[0].isdigit()
                and ":" in s):
            continue
        if s == prev:
            continue
        prev = s
        lines_out.append(s)
    return _dedupe_tail(lines_out)


def _parse_vtt(path: Path) -> list[str]:
    return _parse_vtt_text(
        path.read_text(encoding="utf-8", errors="replace"))


def _parse_json3_data(data: dict) -> list[str]:
    segs = []
    for ev in data.get("events", []):
        txt = "".join(seg.get("utf8", "") for seg in ev.get("segs", []))
        txt = txt.replace("\n", " ").strip()
        if txt:
            segs.append(txt)
    return _dedupe_tail(segs)


def _parse_json3(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    return _parse_json3_data(data)


def _dedupe_tail(segs: list[str]) -> list[str]:
    """Auto captions repeat the cue tail across cues - keep only new text."""
    out, joined_prev = [], ""
    for s in segs:
        if joined_prev.endswith(s):
            continue
        overlap = max((k for k in range(1, min(len(s), len(joined_prev)) + 1)
                       if joined_prev.endswith(s[:k])), default=0)
        piece = s[overlap:].strip()
        if piece:
            out.append(piece)
        joined_prev = (joined_prev + " " + s).strip()
    return out


def _api_transcript(video_id: str) -> list[str]:
    """Primary path on runners: the caption API speaks a different endpoint
    than the video player, so it is not behind the bot-check wall."""
    langs = CONFIG["sub_langs"]
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return []
    try:
        api = YouTubeTranscriptApi()
        try:
            for t in api.list(video_id):
                if str(getattr(t, "language_code", "")).startswith(
                        tuple(CONFIG["sub_langs"])):
                    fetched = t.fetch()
                    return [s.text.replace("\n", " ").strip()
                            for s in fetched if s.text]
        except Exception as exc:            # noqa: BLE001 - fall through
            print(f"[pdrip] caption list: {type(exc).__name__}: "
                  f"{str(exc)[:140]}")
        fetched = api.fetch(video_id, languages=langs)
        return [s.text.replace("\n", " ").strip() for s in fetched if s.text]
    except Exception as exc:                # noqa: BLE001 - report honestly
        print(f"[pdrip] caption API: {type(exc).__name__}: "
              f"{str(exc)[:140]}")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi as Legacy
        rows = Legacy.get_transcript(video_id, languages=langs)
        return [r.get("text", "").replace("\n", " ").strip() for r in rows
                if r.get("text")]
    except Exception as exc:                # noqa: BLE001 - report and move on
        print(f"[pdrip] caption legacy: {type(exc).__name__}: "
              f"{str(exc)[:140]}")
        return []


def _invidious_bases() -> list[str]:
    """Live instance list, health-sorted; static fallback on any failure."""
    import requests
    try:
        r = requests.get("https://api.invidious.io/instances.json",
                         params={"sort_by": "health"}, timeout=15)
        if r.ok:
            uris = []
            for entry in r.json():
                if not (isinstance(entry, list) and len(entry) > 1
                        and isinstance(entry[1], dict)):
                    continue
                meta = entry[1]
                if meta.get("type") == "https" and meta.get("api"):
                    uris.append(str(meta.get("uri", "")).rstrip("/"))
            if uris:
                return uris[:6]
    except Exception:                       # noqa: BLE001 - static list
        pass
    return CONFIG.get("invidious_proxies", [])


def _proxy_transcript(video_id: str) -> list[str]:
    """Third net: public Piped / Invidious instances proxy caption tracks
    through their own servers - none of them sit behind YouTube's bot
    check, and neither do we."""
    import requests
    for base in CONFIG.get("caption_proxies", []):
        host = base.split("//")[1]
        try:
            r = requests.get(f"{base}/streams/{video_id}", timeout=20)
            if not r.ok:
                print(f"[pdrip] piped {host}: HTTP {r.status_code}")
                continue
            data = r.json()
            if data.get("error"):
                print(f"[pdrip] piped {host}: {str(data['error'])[:80]}")
                continue
            subs = data.get("subtitles") or []
            fa = [s for s in subs
                  if str(s.get("code", "")).startswith(tuple(
                      CONFIG["sub_langs"]))]
            fa = fa or [s for s in subs if s.get("autoGenerated")]
            if not fa and not (data.get("audioStreams") or []):
                print(f"[pdrip] piped {host}: {len(subs)} subs, "
                      "0 usable, no audio")
            for s in fa[:2]:
                cr = requests.get(s["url"], timeout=20)
                if not cr.ok:
                    continue
                body = cr.text
                segs = (_parse_json3_data(json.loads(body))
                        if body.lstrip().startswith("{")
                        else _parse_vtt_text(body))
                if len(" ".join(segs)) > 400:
                    print(f"[pdrip] transcript via {base.split('//')[1]} "
                          f"({len(segs)} cues)")
                    return segs
        except Exception as exc:            # noqa: BLE001 - next instance
            print(f"[pdrip] proxy {base.split('//')[1]}: "
                  f"{type(exc).__name__}")
    for base in _invidious_bases():
        host = base.split("//")[-1]
        try:
            r = requests.get(f"{base}/api/v1/captions/{video_id}",
                             timeout=20)
            if not r.ok:
                print(f"[pdrip] invidious {host}: HTTP {r.status_code}")
                continue
            tracks = r.json()
            if isinstance(tracks, dict):
                tracks = tracks.get("captions") or tracks.get("data") or []
                if isinstance(tracks, dict):
                    tracks = [tracks]
            if not isinstance(tracks, list) or not tracks:
                print(f"[pdrip] invidious {host}: no usable caption list")
                continue
            fa = next((t for t in tracks if isinstance(t, dict)
                       and str(t.get("language_code", "")).startswith(
                           tuple(CONFIG["sub_langs"]))), None)
            fa = fa or next((t for t in tracks if isinstance(t, dict)
                             and t.get("auto_generated")), None)
            if not fa or not fa.get("label"):
                print(f"[pdrip] invidious {host}: {len(tracks)} tracks, "
                      "no fa")
                continue
            cr = requests.get(
                f"{base}/api/v1/captions/{video_id}",
                params={"label": fa["label"]}, timeout=20)
            if not cr.ok:
                print(f"[pdrip] invidious {host}: caption fetch "
                      f"HTTP {cr.status_code}")
                continue
            segs = _parse_vtt_text(cr.text)
            if len(" ".join(segs)) > 400:
                print(f"[pdrip] transcript via {host} ({len(segs)} cues)")
                return segs
        except Exception as exc:            # noqa: BLE001 - next instance
            print(f"[pdrip] invidious {host}: {type(exc).__name__}")
    return []


def transcript(work: Path, audio: Path | None, video_id: str = "",
               source: str = "youtube") -> list[str]:
    for sub in sorted(work.glob("source.*.*")):
        if sub.suffix == ".json3":
            segs = _parse_json3(sub)
        elif sub.suffix == ".vtt":
            segs = _parse_vtt(sub)
        else:
            continue
        if len(" ".join(segs)) > 400:
            print(f"[pdrip] transcript from {sub.suffix[1:]} captions "
                  f"({len(segs)} cues)")
            return segs
    if video_id and source != "aparat":
        segs = _api_transcript(video_id)
        if len(" ".join(segs)) > 400:
            print(f"[pdrip] transcript from caption API ({len(segs)} cues)")
            return segs
        segs = _proxy_transcript(video_id)
        if len(" ".join(segs)) > 400:
            return segs
    if audio is not None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print("[pdrip] no captions and no faster-whisper - skipping video")
            return []
        print("[pdrip] whisper fallback (this is the slow path)...")
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segs, _ = model.transcribe(str(audio), language="fa",
                                   vad_filter=True, beam_size=1)
        return [s.text.strip() for s in segs if s.text.strip()]
    return []


# ----------------------------------------------------------- sanitize ----
_PATTERNS = [re.compile(p, re.IGNORECASE) for p in CONFIG["personal_patterns"]]
_SENT = re.compile(r"[^.!?؟\n]+[.!?؟]?")


def sanitize_fa(segs: list[str]) -> tuple[list[str], int]:
    kept, dropped = [], 0
    for seg in segs:
        if any(w in seg for w in CONFIG["skip_words"]):
            dropped += 1
            continue
        cleaned = seg
        for pat in _PATTERNS:
            cleaned = pat.sub(" ", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        if len(cleaned) < 12:
            dropped += 1
            continue
        kept.append(cleaned)
    return kept, dropped


# ---------------------------------------------------------- translate ----
# deep-translator talks to translate.google.com's HTML endpoint, which
# 429s datacenter IPs on the very first request (run 39189838070: 181/181
# lines rejected for 85 straight minutes). The chain here: Google's gtx
# JSON endpoint (the browser API itself, chunked with newline-joined
# sentences so one request covers ~10 lines) -> MyMemory line by line.
_GTX = ("https://translate.googleapis.com/translate_a/single"
        "?client=gtx&sl=fa&tl=en&dt=t&q=")
_MYMEM = "https://api.mymemory.translated.net/get?langpair=fa|en&q="


def _chunks(lines: list[str], cap: int = 1000):
    buf: list[str] = []
    n = 0
    for s in lines:
        if buf and n + len(s) + 1 > cap:
            yield buf
            buf, n = [], 0
        buf.append(s)
        n += len(s) + 1
    if buf:
        yield buf


def translate(segs: list[str]) -> list[str]:
    import html as htmllib
    import urllib.parse

    import requests
    out: list[str] = []
    n_drop = 0
    for buf in _chunks(segs):
        done = False
        for attempt in range(2):
            try:
                r = requests.get(
                    _GTX + urllib.parse.quote("\n".join(buf)),
                    timeout=25, headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                text = "".join(s[0] for s in r.json()[0] if s[0])
                parts = [p.strip() for p in text.split("\n")]
                if len(parts) == len(buf):
                    out.extend(parts)
                    done = True
                    break
                if len(buf) == 1:
                    out.append(text.strip())
                    done = True
                    break
                break                       # merged lines -> line backend
            except Exception as exc:        # noqa: BLE001 - backoff, then next
                print(f"[pdrip] gtx chunk: {type(exc).__name__}")
                time.sleep(2 + 4 * attempt)
        if done:
            continue
        for line in buf:                    # MyMemory, one line at a time
            pieces = [line[j:j + 440] for j in range(0, len(line), 440)]
            got: list[str] = []
            for piece in pieces:
                text = None
                for attempt in range(3):
                    try:
                        r = requests.get(
                            _MYMEM + urllib.parse.quote(piece), timeout=25)
                        r.raise_for_status()
                        text = htmllib.unescape(
                            r.json()["responseData"]["translatedText"])
                        break
                    except Exception:       # noqa: BLE001 - backoff, then drop
                        time.sleep(1.5 * (attempt + 1))
                if text is None:
                    break
                got.append(text)
                time.sleep(0.45)
            if len(got) == len(pieces):
                out.append(" ".join(got).strip())
            else:
                n_drop += 1
    if n_drop:
        print(f"[pdrip] translate dropped {n_drop} line(s)")
    print(f"[pdrip] translated {len(out)}/{len(segs)} lines")
    return out


# --------------------------------------------------------- build script ----
_STOP = set("the a an and or but of to in on for with is are was were be been "
            "this that it its as at by from you your we our they their not "
            "have has had will would can could should i he she they them".split())


def stock_for(chunk: str, idx: int) -> str:
    low = chunk.lower()
    for key, stock in CONFIG["stock_map"].items():
        if key != "default" and key in low:
            return stock
    generics = ["cinematic nature landscape", "city timelapse night",
                "person walking path", "sky clouds timelapse",
                "ocean waves aerial"]
    return generics[idx % len(generics)]


def make_script(info: dict, en_segs: list[str]) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    src_url = (info.get("webpage_url") or info.get("original_url")
               or info.get("url") or "")
    if not src_url.startswith("http"):
        src_url = f"https://youtu.be/{info.get('id', '')}" if \
            info.get("id") else now.isoformat()
    slug = "pdrip_" + now.strftime("%Y%m%d") + "_" + \
        hashlib.sha1(src_url.encode()).hexdigest()[:6]

    words_per = CONFIG["words_per_scene"]
    chunks, cur = [], []
    for s in en_segs:
        cur.append(s)
        if sum(len(c.split()) for c in cur) >= words_per:
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    chunks = chunks[: CONFIG["max_scenes"]]
    if len(chunks) < 4:
        raise SystemExit("[pdrip] transcript too short after sanitizing")

    scenes = [{"stock": stock_for(c, i), "narration": c.strip()}
              for i, c in enumerate(chunks)]

    title_en = translate([ (info.get("title") or "Personal Development").strip() ])[0]
    title_en = re.sub(r"\s{2,}", " ", title_en).strip()[:95]
    lead = " ".join(en_segs[:2])[:350]
    source_url = src_url

    desc = (f"{lead}\n\n"
            f"Full narration translated from a public Persian video, "
            f"rebuilt with original visuals. New episode every day.\n\n"
            f"Source (public): {source_url}\n\n"
            "#personaldevelopment #selfimprovement #motivation "
            "#habits #discipline #success #psychology #growth "
            "#mindseries")

    words = re.findall(r"[A-Za-z']{5,}", " ".join(en_segs).lower())
    freq: dict[str, int] = {}
    for w in words:
        if w not in _STOP:
            freq[w] = freq.get(w, 0) + 1
    top = [w for w, _ in sorted(freq.items(), key=lambda kv: -kv[1])[:8]]

    return {
        "slug": slug,
        "topic": title_en,
        "title": title_en,
        "orientation": "landscape",
        "voice": VOICE,
        "thumb_text": " ".join(title_en.split()[:5]).upper(),
        "thumb_stock": scenes[0]["stock"],
        "description": desc,
        "tags": top + ["personal development", "self improvement",
                       "motivation", "persian to english"],
        "scenes": scenes,
        "_source": source_url,
        "_source_title_fa": info.get("title", ""),
    }


# ------------------------------------------------------------ thumb ----
def pd_thumb(src_jpg: Path | None, dest: Path, title_en: str) -> None:
    from PIL import Image, ImageDraw, ImageFont
    if src_jpg is None or not src_jpg.exists():
        print("[pdrip] no source thumbnail - keeping the factory one")
        return
    img = Image.open(src_jpg).convert("RGB")
    # crop-to-fill 1920x1080
    tw, th = 1920, 1080
    scale = max(tw / img.width, th / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)))
    left = (img.width - tw) // 2
    top = (img.height - th) // 2
    img = img.crop((left, top, left + tw, top + th))

    d = ImageDraw.Draw(img)
    band = tuple(CONFIG["thumb_band_color"])
    accent = tuple(CONFIG["thumb_accent"])
    yellow = (255, 214, 0)
    d.rectangle([0, 0, tw, 340], fill=band)
    d.rectangle([0, th - 120, tw, th], fill=band)
    d.rectangle([0, 340, tw, 356], fill=accent)

    fp = next((p for p in [r"C:\Windows\Fonts\arialbd.ttf",
                           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
               if Path(p).exists()), None)

    def fit(text: str, box_w: int, start: int) -> tuple:
        size = start
        while fp and size >= 56:
            f = ImageFont.truetype(fp, size)
            if d.textlength(text, font=f) <= box_w:
                return f, size
            size -= 6
        f = ImageFont.truetype(fp, max(size, 40)) if fp \
            else ImageFont.load_default()
        return f, max(size, 40)

    words = title_en.split()
    if len(words) >= 4 and len(title_en) > 26:
        cut, best = len(words), 1 << 30
        for i in range(1, len(words)):
            a = " ".join(words[:i])
            b = " ".join(words[i:])
            bal = abs(len(a) - len(b))
            if bal < best and d.textlength(a, font=ImageFont.load_default()) >= 0:
                best, cut = bal, i
        line1, line2 = " ".join(words[:cut]), " ".join(words[cut:])
    else:
        line1, line2 = title_en, ""

    f, _ = fit(line1, tw - 120, 132)
    d.text((tw // 2, 118), line1, font=f, fill=(255, 255, 255),
           anchor="mm", stroke_width=8, stroke_fill=(0, 0, 0))
    if line2:
        f2, _ = fit(line2, tw - 120, 132)
        d.text((tw // 2, 250), line2, font=f2, fill=yellow,
               anchor="mm", stroke_width=8, stroke_fill=(0, 0, 0))
    uw = int(min(d.textlength(line1, font=f), tw - 320))
    d.rectangle([tw // 2 - uw // 2, 300, tw // 2 + uw // 2, 316],
                fill=accent)

    fs = ImageFont.truetype(fp, 46) if fp else ImageFont.load_default()
    d.text((tw // 2, th - 60),
           "Translated  *  Original visuals  *  New every day",
           font=fs, fill=yellow, anchor="mm", stroke_width=3,
           stroke_fill=(0, 0, 0))
    img.save(dest, "JPEG", quality=90)
    print(f"[pdrip] source-style thumbnail: {dest.name}")


# ------------------------------------------------------------- main ----
def main() -> int:
    global PROF, CONTENT, OUTDIR, CHANNEL, QUERIES, VOICE

    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--channel", default=os.environ.get("PD_CHANNEL", "4"),
                    help="channel profile to render/upload under "
                         "(4 = flagship, 5..104 = multichan categories)")
    args = ap.parse_args()

    CHANNEL = str(args.channel).strip()
    PROF = channels.profile(CHANNEL)
    CONTENT, OUTDIR = PROF["content"], PROF["out"]
    entry = _registry(CHANNEL)
    if entry:
        QUERIES = list(entry["queries"])
        VOICE = entry["voice"]
        print(f"[pdrip] channel {CHANNEL} = {entry['name']} "
              f"({entry['category']}) queries={QUERIES}")

    state = load_state()
    state.setdefault("failed", {})
    # one pair (long + Short) per channel per day; the cron fires a few
    # times and each later wave only exists to rescue a day the earlier
    # waves could not fill.  The count file is the channel's OWN ledger,
    # so one channel publishing never silences another.
    try:
        cnt = json.loads(Path(PROF["count"]).read_text(encoding="utf-8"))
        posted = int(cnt.get("count", 0)) if cnt.get("date") == \
            dt.date.today().isoformat() else 0
    except Exception:                         # noqa: BLE001 - no ledger yet
        posted = 0
    if posted >= int(PROF.get("daily_cap", 2)):
        print(f"[pdrip] channel {CHANNEL} already posted {posted} today "
              "- standing down")
        return 0
    cands = discover(state, args.video or None)
    if not cands:
        return 0

    print(f"[pdrip] {len(cands)} total, trying up to "
          f"{min(5, len(cands))} per run")
    for info in cands[:5]:
        url = (info.get("webpage_url") or info.get("original_url")
               or info.get("url")
               or (f"https://youtu.be/{info['id']}" if info.get("id") else ""))
        if not url or url in state["processed"]:
            print(f"[pdrip] skip: {url[:70] or '<no url>'} "
                  f"({'dup' if url else 'no url at all'})")
            continue
        print(f"[pdrip] candidate: {info.get('title', '')[:60]}")

        work = PROF["work"] / (info.get("id") or "forced")
        work.mkdir(parents=True, exist_ok=True)
        vid = info.get("id") or ""
        src = info.get("source", "youtube")
        if src == "aparat":
            thumb_jpg = fetch_aparat_poster(info, work)
            audio = download_aparat(info, work)
        else:
            thumb_jpg = fetch_thumb(vid, work) if vid else None
            # the player sits behind the bot-check on datacenter IPs, so
            # the audio may never arrive - it is best effort; the output
            # never uses source audio anyway
            audio, dl_thumb = download(url, work, src)
            if thumb_jpg is None:
                thumb_jpg = dl_thumb
            if audio is None and vid:
                audio = _proxy_audio(vid, work)
        segs_fa = transcript(work, audio, vid, src)
        if not segs_fa:
            print(f"[pdrip] no transcript from {src} - next candidate")
            _fail(state, url, "no transcript")
            continue
        clean_fa, dropped = sanitize_fa(segs_fa)
        print(f"[pdrip] fa cues {len(segs_fa)} -> clean {len(clean_fa)} "
              f"(dropped {dropped} personal/promo)")
        en = translate(clean_fa)
        if len(" ".join(en)) < 300:
            print("[pdrip] translation too short - next candidate")
            _fail(state, url, "translation too short")
            continue

        script = make_script(info, en)
        CONTENT.mkdir(parents=True, exist_ok=True)
        OUTDIR.mkdir(parents=True, exist_ok=True)
        src_json = CONTENT / f"{script['slug']}.json"
        src_json.write_text(json.dumps(script, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"[pdrip] script: {script['slug']} "
              f"({len(script['scenes'])} scenes)")

        rc = subprocess.run(
            [sys.executable, str(FACTORY / "factory.py"),
             "--batch", "--channel", CHANNEL, "--only", script["slug"]],
            encoding="utf-8", errors="replace").returncode
        if rc != 0:
            print("[pdrip] render failed - not marking as processed")
            save_state(state)
            return rc

        pd_thumb(thumb_jpg, OUTDIR / f"{script['slug']}.jpg",
                 script["title"])

        # one Short per long: same story condensed, portrait, factory's
        # own thumbnail (1080x1920, the style every other channel uses)
        short_slug = ""
        try:
            import make_shorts
            short = make_shorts.make_short(script)
            short_slug = short["slug"]
            (CONTENT / f"{short_slug}.json").write_text(
                json.dumps(short, ensure_ascii=False, indent=2),
                encoding="utf-8")
            sr = subprocess.run(
                [sys.executable, str(FACTORY / "factory.py"),
                 "--batch", "--channel", CHANNEL, "--only", short_slug],
                encoding="utf-8", errors="replace").returncode
            if sr != 0:
                print("[pdrip] short render failed - long still ships")
                short_slug = ""
            else:
                print(f"[pdrip] short ready: {short_slug}")
        except Exception as exc:            # noqa: BLE001 - short is a bonus
            print(f"[pdrip] short skipped: {type(exc).__name__}: {exc}")
            short_slug = ""

        if args.no_upload:
            print("[pdrip] --no-upload: render ready, stopping here")
        elif not os.environ.get(PROF["token_env"], "").strip():
            print(f"[pdrip] {PROF['token_env']} not set - render ready, "
                  "upload skipped")
        else:
            up = subprocess.run(
                [sys.executable, str(FACTORY / "upload.py"),
                 "--channel", CHANNEL,
                 "--only", f"{script['slug']} {short_slug}".strip()],
                encoding="utf-8", errors="replace")
            if up.returncode != 0:
                print("[pdrip] upload failed - not marking as processed")
                save_state(state)
                return up.returncode

        state["processed"][url] = {
            "slug": script["slug"], "title_en": script["title"],
            "source_title": script["_source_title_fa"],
            "date": dt.date.today().isoformat(),
            "scenes": len(script["scenes"]),
        }
        state["failed"].pop(url, None)
        save_state(state)
        print(f"[pdrip] done: {script['slug']}")
        return 0

    save_state(state)
    print("[pdrip] every candidate failed today - nothing published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
