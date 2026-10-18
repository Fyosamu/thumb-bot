"""Free, fully-local YouTube video factory.

pipeline (no paid APIs):
  script JSON  ->  edge-tts (free)  ->  Pexels stock footage (free)
               ->  ffmpeg assemble  ->  PIL thumbnail  ->  YouTube upload

Usage:
    python factory.py --list
    python factory.py --render  <script.json>
    python factory.py --batch              # render every script still queued
"""
from __future__ import annotations

import argparse
import os
import json
import shutil
import subprocess
import re
import sys
import textwrap
from pathlib import Path

import channels as channel_profiles

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content"          # script JSONs live here (channel 1)
WORK = HERE / "work"                # per-video scratch space
OUT = HERE / "out"                  # finished mp4s
for d in (CONTENT, WORK, OUT):
    d.mkdir(parents=True, exist_ok=True)

# Windows carries the Arial pair; the Linux runner swaps in DejaVu, which
# measures close enough that every auto-shrink loop still fits.
_LINUX_FONTS = {"arialbd.ttf": "DejaVuSans-Bold.ttf",
                "arial.ttf": "DejaVuSans.ttf"}


def _font_path(name: str) -> Path | None:
    win = Path(r"C:\Windows\Fonts") / name
    if win.exists():
        return win
    lin = Path("/usr/share/fonts/truetype/dejavu") / _LINUX_FONTS[name]
    return lin if lin.exists() else None

FFMPEG = shutil.which("ffmpeg") or str(
    Path(r"C:\Users\USER\AppData\Local\Microsoft\WinGet\Packages"
         r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
         r"\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"))
FFPROBE = shutil.which("ffprobe") or str(Path(FFMPEG).with_name("ffprobe.exe"))

PEXELS_KEY = os.environ.get(
    "PEXELS_KEY",
    "DlTa4XKMzuGCvBy2bTTfvul2JP18DPM1LXYs4wHyHhRnrLqfJ9i55sm8")

# a long has to clear ten minutes (mid-roll ads), a Short has to stay
# under the one-minute ceiling YouTube gives the format
MIN_LONG = 630.0
MAX_SHORT = 57.0


def run(cmd: list[str], quiet: bool = True) -> None:
    p = subprocess.run(cmd, capture_output=quiet, text=True)
    if p.returncode != 0:
        tail = (p.stderr or p.stdout or "")[-1200:]
        raise RuntimeError(f"cmd failed ({p.returncode}): {' '.join(cmd[:4])}...\n{tail}")


def duration_of(path: Path) -> float:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True,
    ).stdout.strip()
    return float(out or 0)


def resolve_assets(script: dict, folder: Path, orientation: str) -> list[Path]:
    """Download one Pexels clip per scene, sized for the target orientation.

    The search is retried a few times with a backoff: Pexels drops
    connections now and then and a single timeout used to kill a render
    that had already paid for its TTS.
    """
    import time as _time

    import requests

    def search(params: dict) -> list:
        last = None
        for attempt in range(6):
            try:
                r = requests.get("https://api.pexels.com/videos/search",
                                 params=params,
                                 headers={"Authorization": PEXELS_KEY},
                                 timeout=30)
                r.raise_for_status()
                return r.json().get("videos", [])
            except Exception as exc:  # noqa: BLE001
                last = exc
                print(f"        pexels attempt {attempt + 1}/6 failed "
                      f"({type(exc).__name__}) - retrying")
                _time.sleep(3 + attempt * 4)
        raise RuntimeError(f"pexels unreachable for "
                           f"{params.get('query')!r}: {last}")

    folder.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    want_h = 1080 if orientation == "landscape" else 1920
    want_w = 1920 if orientation == "landscape" else 1080

    for i, scene in enumerate(script["scenes"]):
        dest = folder / f"scene{i:02d}.mp4"
        if dest.exists() and dest.stat().st_size > 100_000:
            clips.append(dest)
            continue
        params = {"query": scene["stock"], "per_page": 6, "orientation": orientation}
        videos = search(params)
        if not videos:
            raise RuntimeError(f"no pexels results for {scene['stock']!r}")

        # prefer a file at exactly the target resolution, else nearest
        chosen = None
        for v in videos:
            files = [f for f in v.get("video_files", [])
                     if f.get("height") and f.get("width")]
            exact = [f for f in files
                     if f["height"] == want_h and f["width"] == want_w]
            if exact:
                chosen = exact[0]
                break
        if chosen is None:
            for v in videos:
                files = [f for f in v.get("video_files", []) if f.get("height")]
                if files:
                    chosen = min(files, key=lambda f: abs(f["height"] - want_h))
                    break
        if chosen is None:
            raise RuntimeError(f"no usable file for {scene['stock']!r}")

        last = None
        for attempt in range(5):
            try:
                with requests.get(chosen["link"], stream=True,
                                  timeout=120) as dl:
                    dl.raise_for_status()
                    with dest.open("wb") as fh:
                        for chunk in dl.iter_content(1 << 20):
                            fh.write(chunk)
                if dest.stat().st_size > 100_000:
                    break
                raise RuntimeError("clip came back truncated")
            except Exception as exc:  # noqa: BLE001
                last = exc
                dest.unlink(missing_ok=True)
                print(f"        clip download {attempt + 1}/5 failed "
                      f"({type(exc).__name__}) - retrying")
                _time.sleep(3 + attempt * 4)
        else:
            raise RuntimeError(f"could not download "
                               f"{scene['stock']!r}: {last}")
        clips.append(dest)
    return clips


PIPER_VOICE_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "piper" / "voices"


def _piper_model() -> "Path | None":
    """The local neural voice model, if one has been downloaded."""
    if not PIPER_VOICE_DIR.is_dir():
        return None
    models = sorted(PIPER_VOICE_DIR.glob("*.onnx"))
    return models[0] if models else None


def _piper_tts(text: str, dest: Path, model: Path) -> None:
    """Synthesize with piper, then mux to mp3 so nothing downstream changes."""
    import subprocess as _sp

    wav = dest.with_suffix(".wav")
    _sp.run([sys.executable, "-m", "piper", "--model", str(model),
             "--output-file", str(wav)],
            input=text, text=True, capture_output=True, check=True)
    run([FFMPEG, "-y", "-i", str(wav), "-b:a", "128k", str(dest)])
    wav.unlink(missing_ok=True)


def long_rate(script: dict) -> str:
    """Speech rate for a landscape episode.

    A long has to clear ten minutes for mid-roll ads, and a short has to
    stay under sixty seconds, so the rate is derived from the word count
    instead of being hard-coded: -5% when the narration already runs long
    enough, slower only when it would otherwise fall short.
    """
    words = sum(len(s.get("narration", "").split())
                for s in script.get("scenes", []))
    est = words / 186.0 * 60.0              # seconds at -5%, measured
    if est >= 645.0:
        return "-5%"
    factor = 645.0 / max(est, 1.0)
    r = 0.95 / factor - 1.0                 # duration scales with 1/(1+r)
    return f"{max(-30, round(r * 100))}%"


def make_tts(script: dict, folder: Path, voice: str,
             rate: str = "-5%") -> list[Path]:
    """One mp3 per scene; returns them in scene order.

    edge-tts is always tried first, so the requested voice is used whenever
    the service is reachable.  Microsoft migrated its speech API in October
    2026 and edge-tts can no longer authenticate, so anything it fails on is
    retried with piper - a local neural voice - to keep rendering alive.
    """
    import asyncio

    import edge_tts

    folder.mkdir(parents=True, exist_ok=True)
    jobs = [(folder / f"voice{i:02d}.mp3", scene["narration"])
            for i, scene in enumerate(script["scenes"])]

    async def synth(text: str, dest: Path) -> None:
        await edge_tts.Communicate(text, voice, rate=rate).save(str(dest))

    async def main() -> None:
        for dest, text in jobs:
            if dest.exists() and dest.stat().st_size > 1000:
                continue
            await synth(text, dest)

    failed: list = []
    try:
        asyncio.run(main())
    except Exception as exc:                     # the speech service is down
        print(f"    edge-tts failed ({type(exc).__name__}) - "
              "falling back to the local piper voice")
        failed = jobs                            # files already written stay valid

    if failed:
        model = _piper_model()
        if model is None:
            raise RuntimeError(
                "edge-tts is unreachable and no piper voice is installed.  "
                "Run: python -m piper.download_voices en_US-lessac-medium")
        for dest, text in failed:
            if dest.exists() and dest.stat().st_size > 1000:
                continue
            _piper_tts(text, dest, model)

    return [d for d, _ in jobs]


def normalize_length(voices: list[Path], durs: list[float], folder: Path,
                     orientation: str) -> tuple[list[Path], list[float]]:
    """Stretch or trim narration so the finished cut lands in its window.

    Longs must clear ten minutes for mid-roll ads, Shorts must stay under
    a minute, and neither the edge-tts nor the piper fallback reproduces
    the word count exactly - so the length is enforced after the fact with
    atempo, which changes tempo while keeping the voice's pitch.  The
    slow-down is capped, because speech stretched past ~20% stops sounding
    like a person talking.
    """
    total = sum(durs)
    if orientation == "landscape":
        target, direction = MIN_LONG, "down"
    else:
        target, direction = MAX_SHORT, "up"
    if direction == "down" and total >= target:
        return voices, durs
    if direction == "up" and total <= target:
        return voices, durs
    if total <= 0:
        return voices, durs

    tempo = total / target                      # <1 slows, <1 speeds
    if direction == "down":
        tempo = max(tempo, 0.78)                # never slower than -22%
    else:
        tempo = min(tempo, 1.45)                # never faster than +45%

    slow = folder / "timed"
    slow.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for i, v in enumerate(voices):
        dest = slow / f"{i:02d}{v.suffix}"
        if not dest.exists():
            run([FFMPEG, "-y", "-i", str(v), "-filter:a", f"atempo={tempo:.4f}",
                 "-b:a", "160k", str(dest)])
        out.append(dest)
    durs = [duration_of(v) for v in out]
    print(f"        timed to {sum(durs):.1f}s (atempo {tempo:.3f})")
    return out, durs


GAP = 0.04                          # clean frames between two caption boxes


def _wrap_caption(text: str, font, draw, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if cur and draw.textlength(cand, font=font) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def _caption_png(text: str, dest: Path, vw: int, vh: int,
                 orientation: str) -> Path:
    """One caption: gold text on a black 75%-opaque pill with round corners."""
    from PIL import Image, ImageDraw, ImageFont

    face = _font_path("arialbd.ttf") or _font_path("arial.ttf")
    face = str(face) if face else None
    size = int(vh * 0.045) if orientation == "landscape" else int(vw * 0.042)
    font = ImageFont.truetype(face, size) if face else ImageFont.load_default()
    canvas = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    max_w = int(vw * 0.84)

    lines = _wrap_caption(text, font, draw, max_w)
    while face and size > 20 and (
            len(lines) > 2
            or max(draw.textlength(l, font=font) for l in lines) > max_w):
        size = int(size * 0.92)
        font = ImageFont.truetype(face, size)
        lines = _wrap_caption(text, font, draw, max_w)

    pad_x, pad_y = int(size * 0.80), int(size * 0.42)
    line_h = int(size * 1.14)
    text_w = int(max(draw.textlength(l, font=font) for l in lines))
    box_w, box_h = text_w + pad_x * 2, line_h * len(lines) + pad_y * 2
    x = (vw - box_w) // 2
    # portrait Shorts keep the caption low: mid-screen collides with the
    # on-screen UI and reads as "in the middle of the frame"
    y = int(vh * 0.79) if orientation == "landscape" else int(vh * 0.92)
    draw.rounded_rectangle([x, y, x + box_w, y + box_h],
                           radius=int(box_h * 0.30), fill=(0, 0, 0, 191))
    ty = y + pad_y
    for line in lines:
        lw = draw.textlength(line, font=font)
        draw.text((x + (box_w - lw) / 2, ty), line, font=font,
                  fill=(255, 214, 10, 255))
        ty += line_h
    canvas.save(dest)
    return dest


def make_captions(script: dict, durs: list[float], work: Path,
                  vw: int, vh: int, orientation: str
                  ) -> list[list[tuple[Path, float, float]]]:
    """Burned-in subtitles, one box per narration chunk.

    Windows run strictly forward - the next box starts a frame after the
    previous one ends - so two captions can never share a frame.  Every
    scene is assembled in its own ffmpeg part, which keeps scenes apart.
    """
    cap_dir = work / "caps"
    cap_dir.mkdir(exist_ok=True)
    max_chars = 48 if orientation == "landscape" else 34
    out: list[list[tuple[Path, float, float]]] = []

    for i, scene in enumerate(script["scenes"]):
        chunks, cur = [], ""
        for word in scene["narration"].split():
            cand = f"{cur} {word}".strip()
            if len(cand) > max_chars and cur:
                chunks.append(cur)
                cur = word
            else:
                cur = cand
        if cur:
            chunks.append(cur)

        total_chars = sum(len(c) for c in chunks) or 1
        boxes: list[tuple[Path, float, float]] = []
        t = 0.0
        for k, chunk in enumerate(chunks):
            span = durs[i] * len(chunk) / total_chars
            start, end = t, min(t + span, durs[i])
            t = end
            if k < len(chunks) - 1:
                end -= GAP
            if end - start > 0.08:
                png = _caption_png(chunk, cap_dir / f"c{i:02d}_{k:02d}.png",
                                   vw, vh, orientation)
                boxes.append((png, start, end))
        for prev, nxt in zip(boxes, boxes[1:]):
            if nxt[1] < prev[2]:
                raise RuntimeError(
                    f"caption overlap in scene {i}: {prev[2]:.2f} > {nxt[1]:.2f}")
        out.append(boxes)
    return out


def build(script: dict, work: Path, orientation: str) -> Path:
    vw, vh = (1920, 1080) if orientation == "landscape" else (1080, 1920)

    print("  [1/5] tts (edge-tts, free)")
    rate = long_rate(script) if orientation == "landscape" else "-5%"
    voices = make_tts(script, work / "voice",
                      script.get("voice", "en-US-AvaMultilingualNeural"), rate)
    durs = [duration_of(v) for v in voices]
    print(f"        {len(voices)} segments, {sum(durs):.1f}s total")
    voices, durs = normalize_length(voices, durs, work, orientation)

    print("  [2/5] stock footage (pexels, free)")
    clips = resolve_assets(script, work / "clips", orientation)

    print("  [3/5] captions (PIL)")
    caps = make_captions(script, durs, work, vw, vh, orientation)
    print(f"        {sum(len(c) for c in caps)} boxes, "
          "windows strictly sequential")

    print("  [4/5] assemble (ffmpeg)")
    parts_dir = work / "parts"
    parts_dir.mkdir(exist_ok=True)
    parts: list[Path] = []
    for i, (clip, dur, voice) in enumerate(zip(clips, durs, voices)):
        part = parts_dir / f"part{i:02d}.mp4"
        vf = (f"scale={vw}:{vh}:force_original_aspect_ratio=increase,"
              f"crop={vw}:{vh},fps=30,setsar=1")
        if caps[i]:
            # burn this scene's caption boxes, each inside its own window
            fc = f"[0:v]{vf}[base]"
            cur = "[base]"
            for k, (_png, s, e) in enumerate(caps[i]):
                nxt = "[vout]" if k == len(caps[i]) - 1 else f"[v{k}]"
                fc += (f";{cur}[{k + 2}:v]overlay=0:0"
                       f":enable='between(t,{s:.3f},{e:.3f})'{nxt}")
                cur = nxt
            cmd = [FFMPEG, "-y", "-stream_loop", "-1", "-i", str(clip),
                   "-i", str(voice)]
            for png, _s, _e in caps[i]:
                cmd += ["-i", str(png)]
            cmd += ["-filter_complex", fc, "-map", "[vout]", "-map", "1:a",
                    "-t", f"{dur:.3f}", "-r", "30",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                    "-shortest", str(part)]
            run(cmd)
        else:
            run([FFMPEG, "-y", "-stream_loop", "-1", "-i", str(clip),
                 "-i", str(voice), "-t", f"{dur:.3f}",
                 "-vf", vf, "-r", "30",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                 "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                 "-shortest", str(part)])
        parts.append(part)

    concat_list = work / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    merged = work / "merged.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", str(merged)])

    print("  [5/5] thumbnail (PIL)")
    thumb = None
    try:
        thumb = make_thumbnail(script, work / "thumb.jpg", vw, vh)
    except Exception as exc:  # noqa: BLE001
        print(f"        thumbnail skipped: {exc}")

    OUT.mkdir(exist_ok=True)
    final = OUT / f"{script['slug']}.mp4"
    if final.exists():
        final.unlink()
    shutil.move(str(merged), str(final))
    if thumb:
        shutil.copyfile(thumb, OUT / f"{script['slug']}.jpg")
    print(f"  -> {final}")
    return final


def part_number(script: dict) -> int:
    """Episode number for the thumbnail stamp.

    The long and the short that summarises it share one number, and the
    number comes from the alphabetically ordered long list rather than
    from the daily cursor - so re-rendering an episode never renumbers
    it, and two channels never inherit each other's numbering (each
    reads its own CONTENT folder).
    """
    slug = str(script.get("slug", ""))
    stem = re.sub(r"_short\d*$", "", slug)
    # mass-generated scripts (m00001.json, b00000.json ...) are bank
    # material, not episodes - counting them would stamp a fresh channel
    # with "PART 169" the moment the bank is larger than the series
    longs = sorted(p.stem for p in CONTENT.glob("*.json")
                   if "_short" not in p.stem
                   and not re.match(r"^[a-z]\d{5}$", p.stem))
    try:
        return longs.index(stem) + 1
    except ValueError:
        return 0


def subject_name(script: dict) -> str:
    """The person a biography episode is about - drives the face photo."""
    t = str(script.get("title", ""))
    if "'s " in t:
        return t.split("'s ")[0].strip()
    for sep in (" — ", " – ", " | ", " - "):
        if sep in t:
            return t.split(sep)[0].strip()
    return t.strip()


def commons_photo(name: str, orientation: str, cache: Path):
    """A face photo from Wikimedia Commons IN THE FORMAT THE CANVAS NEEDS:
    landscape for the long, portrait for the short.  The article's own
    lead image is almost always a vertical painting, which forced the
    ugly blurred-side composition - Commons search returns the sizes up
    front, so the aspect is chosen before the download.  Commons is also
    its own host with its own rate bucket, which keeps thumbnails alive
    while the enwiki api is busy throttling the topic crawlers."""
    import io
    import time
    import urllib.parse
    import requests
    from PIL import Image

    if cache.exists() and cache.stat().st_size > 2048:
        try:
            hit = Image.open(cache).convert("RGB")
            want_land = orientation == "landscape"
            if (want_land and hit.width >= hit.height * 1.1) or \
               (not want_land and hit.height >= hit.width * 1.05):
                return hit
        except Exception:  # noqa: BLE001
            pass
    ua = "Mozilla/5.0 (compatible; factory-thumb/1.0)"
    q = urllib.parse.urlencode({
        "action": "query", "generator": "search",
        "gsrsearch": f'"{name}" portrait filetype:bitmap',
        "gsrnamespace": "6", "gsrlimit": "40",
        "prop": "imageinfo", "iiprop": "url|size|mime",
        "iiurlwidth": "1600", "format": "json"})
    bad_words = ("coat of arms", "signature", "flag", "map", "logo", "seal",
                 "emblem", "stamp", "coin", "banknote", "banner", "monument",
                 "statue", "grave", "plaque", "diagram", "chart", "plan",
                 "poster", "manuscript", "barcode", "qr", "screenshot",
                 "reverse", "verso", "recto", "rear", "back of", "rückseite",
                 "comparison", "side by side", " collage")
    for attempt in range(4):
        try:
            r = requests.get("https://commons.wikimedia.org/w/api.php?" + q,
                             headers={"User-Agent": ua}, timeout=30)
            if r.status_code == 429:
                wait = min(int(r.headers.get("Retry-After") or 20)
                           * (attempt + 1), 60)
                print(f"        commons throttled, waiting {wait}s")
                time.sleep(wait)
                continue
            if not r.ok:
                return None
            pages = (r.json().get("query") or {}).get("pages") or {}
            want_land = orientation == "landscape"
            # rank for FACES: only a strong face signal passes - a sheet
            # music scan or an exhibition hall with his paintings in the
            # background is the right format and the wrong subject, and
            # when nothing face-like survives the article lead (the
            # canonical portrait) or stock takes over
            face_kw = ("portrait", "portr", "self", "bildnis", "abbild",
                       "photograph", "bust", "face", "head", "gravure",
                       "engraving", "zeichnis", "ritratto", "retrato")
            place_kw = ("view", "exhibition", "museum", "house", "church",
                        "street", "panorama", "interior", "exterior",
                        "building", "castle", "palace", "square", "bridge",
                        "ceremony", "congress", "delegation", "visit",
                        "group", "statue", "monument", "funeral",
                        "ausstellung", "im zeichen", "genialität", "galerie",
                        "gallery", "symposium", "kongress", "tagung",
                        "denkmal", "vernissage", "workshop",
                        "with ", " und ", " & ", " and ")
            cands = []
            for page in pages.values():
                info = (page.get("imageinfo") or [{}])[0]
                w, h = info.get("width", 0), info.get("height", 0)
                title = str(page.get("title", "")).lower()
                if info.get("mime") not in ("image/jpeg", "image/png"):
                    continue
                if w < 900 or h < 600:
                    continue
                if any(b in title for b in bad_words):
                    continue
                if want_land and w < h * 1.15:
                    continue
                if not want_land and h < w * 1.05:
                    continue
                rank = 0
                if any(k in title for k in face_kw):
                    rank += 2
                if name.lower() in title:
                    rank += 1
                if any(k in title for k in place_kw):
                    rank -= 3
                cands.append((rank, w * h,
                              info.get("thumburl") or info.get("url"),
                              page.get("title", "")))
            if not cands:
                return None
            cands.sort(key=lambda c: (c[0], c[1]), reverse=True)
            if cands[0][0] < 2:
                return None      # no strong face signal - article lead instead
            img = requests.get(cands[0][2], headers={"User-Agent": ua},
                               timeout=60)
            if img.ok and len(img.content) > 4096:
                cache.write_bytes(img.content)
                print(f"        commons photo: {cands[0][3]}")
                return Image.open(io.BytesIO(img.content)).convert("RGB")
            return None
        except Exception:  # noqa: BLE001
            time.sleep(3)
    return None


def wiki_photo(name: str, cache: Path):
    """The subject's own lead image from Wikipedia: a biography thumbnail
    shows the person the video is about, never stock pencils.

    REST summary first - api.php gets hammered by the script generators and
    answers 429, while rest_v1 keeps its own bucket."""
    import io
    import time
    import urllib.parse
    import requests
    from PIL import Image

    if cache.exists() and cache.stat().st_size > 1024:
        try:
            return Image.open(cache).convert("RGB")
        except Exception:  # noqa: BLE001
            pass
    ua = "Mozilla/5.0 (compatible; factory-thumb/1.0)"
    slug = urllib.parse.quote(name.replace(" ", "_"), safe="")
    endpoints = [
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
        # the article page itself: og:image lives in the HTML and rides a
        # different rate bucket than the api hosts, so it answers when the
        # summary endpoints are busy throttling
        f"https://en.wikipedia.org/wiki/{slug}",
        "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": name, "prop": "pageimages",
            "piprop": "original", "redirects": "1", "format": "json"}),
    ]
    for attempt in range(6):
        for url in endpoints:
            try:
                r = requests.get(url, headers={"User-Agent": ua}, timeout=25)
                if r.status_code == 429:
                    wait = min(int(r.headers.get("Retry-After") or 20)
                               * (attempt + 1), 60)
                    print(f"        wiki photo throttled, waiting {wait}s")
                    time.sleep(wait)
                    continue
                if not r.ok:
                    continue
                src = None
                if "api.php" in url or "rest_v1" in url:
                    data = r.json()
                    src = (data.get("originalimage") or {}).get("source")
                    if not src:
                        pages = data.get("query", {}).get("pages", {})
                        src = next((p.get("original", {}).get("source")
                                    for p in pages.values()
                                    if p.get("original")), None)
                else:
                    m = re.search(r'<meta property="og:image" content="([^"]+)"',
                                  r.text)
                    src = m.group(1) if m else None
                if not src:
                    continue
                img = requests.get(src, headers={"User-Agent": ua}, timeout=45)
                if img.ok and len(img.content) > 4096:
                    cache.write_bytes(img.content)
                    return Image.open(io.BytesIO(img.content)).convert("RGB")
            except Exception:  # noqa: BLE001
                continue
        time.sleep(4)
    return None


def make_thumbnail(script: dict, dest: Path, vw: int, vh: int) -> Path:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import requests

    bg_url = script.get("thumb_stock") or script["scenes"][0]["stock"]
    photo = None
    import time as _t
    orientation = "portrait" if vh > vw else "landscape"

    # biography: a face photo - Commons first (already in the canvas's
    # own format), then the article's own lead portrait, which is
    # usually vertical and gets face-cropped into the landscape canvas;
    # stock only survives when the person has no wiki image at all
    is_subject = False
    if CONTENT.name == "content_bio":
        who = subject_name(script)
        # Commons landscape search is a minefield of wooden panel backs
        # and comparison plates - the long takes the article's own lead
        # portrait and face-crops it; only the short (true verticals
        # exist) asks Commons for a format-matched portrait first
        if orientation == "portrait":
            photo = commons_photo(
                who, orientation,
                dest.with_suffix(f".{orientation}.face.jpg"))
        if photo is None:
            photo = wiki_photo(who, dest.with_suffix(".lead.jpg"))
        is_subject = photo is not None
    elif CONTENT.name == "content":
        # science: the thumbnail must BE about the topic - the article's
        # own lead image (portrait, diagram, painting - whatever the
        # topic carries), cropped into the canvas, same caption strip as
        # the biography channel; stock only when the topic has no image
        who = script.get("topic") or script["title"].split(" — ")[0]
        photo = wiki_photo(who, dest.with_suffix(".lead.jpg"))
        is_subject = photo is not None

    for attempt in (range(5) if photo is None else ()):
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                             params={"query": bg_url, "per_page": 1,
                                     "orientation": orientation},
                             headers={"Authorization": PEXELS_KEY}, timeout=30)
            if r.ok and r.json().get("photos"):
                src = r.json()["photos"][0]["src"]["large2x"]
                img_r = requests.get(src, timeout=60)
                if img_r.ok:
                    tmp = dest.with_suffix(".src.jpg")
                    tmp.write_bytes(img_r.content)
                    photo = Image.open(tmp).convert("RGB")
                    break
        except Exception as exc:  # noqa: BLE001
            print(f"        thumb source {attempt + 1}/5 failed "
                  f"({type(exc).__name__})")
        _t.sleep(3 + attempt * 4)

    if photo is None:
        # the network can drop mid-batch - the photo saved by the
        # previous render is still on disk and keeps the thumbnail
        # on-brand instead of falling back to a black canvas
        cached = dest.with_suffix(".src.jpg")
        if cached.exists():
            try:
                photo = Image.open(cached).convert("RGB")
                print("        thumb source: reused the cached photo")
            except Exception:  # noqa: BLE001
                photo = None
    if photo is None:
        photo = Image.new("RGB", (vw, vh), (18, 18, 24))
    # the photo always matches the canvas orientation now (the commons
    # search filters by aspect before downloading) - plain cover-fit,
    # no bars and no blurred sides; only stock gets the light blur
    scale = max(vw / photo.width, vh / photo.height)
    photo = photo.resize((int(photo.width * scale),
                          int(photo.height * scale)), Image.LANCZOS)
    ox = (photo.width - vw) // 2
    oy = (photo.height - vh) // 2
    if is_subject and photo.height > vh:
        oy = int((photo.height - vh) * 0.15)   # faces live up top
    photo = photo.crop((ox, oy, ox + vw, oy + vh))
    if not is_subject:
        photo = photo.filter(ImageFilter.GaussianBlur(2))

    draw = ImageDraw.Draw(photo, "RGBA")

    text = script.get("thumb_text") or script["title"]
    font_size = int(vh * (0.13 if len(text) < 34 else 0.105))
    face = _font_path("arialbd.ttf") or _font_path("arial.ttf")
    face = str(face) if face else None
    font = ImageFont.truetype(face, font_size) if face else ImageFont.load_default()

    lines = textwrap.wrap(text.upper(), width=18)[:3]
    # portrait canvases are narrow: keep shrinking until the widest line fits
    while face and lines and font_size > 48:
        widest = max(draw.textlength(line, font=font) for line in lines)
        if widest <= vw * 0.90:
            break
        font_size = int(font_size * 0.9)
        font = ImageFont.truetype(face, font_size)
    # the block also hugs the BOTTOM: shrink until it fits the low band,
    # then anchor it there - the decree is "much, much lower"
    while face and lines and len(lines) * font_size * 1.12 > vh * 0.34 \
            and font_size > 48:
        font_size = int(font_size * 0.9)
        font = ImageFont.truetype(face, font_size)
    y = int(vh * 0.95 - len(lines) * font_size * 1.12)
    # the black bar is a caption strip now: it rides just above the text
    # block with a small gap, so the face owns the rest of the frame
    draw.rectangle([0, max(0, y - int(vh * 0.035)), vw, vh],
                   fill=(0, 0, 0, 150))
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (vw - w) / 2
        draw.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0, 230))
        draw.text((x, y), line, font=font, fill=(255, 214, 10, 255))
        y += int(font_size * 1.12)

    # no PART stamp here: only chess carries the part counter (its own
    # chess_factory does the stamping) — science and biography stay clean

    photo.save(dest, quality=93)
    return dest


def main() -> int:
    global CONTENT, WORK, OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--render")
    ap.add_argument("--batch", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="",
                    help="space-separated slugs to render (or 'all'); skips "
                         "anything already sitting in out/")
    ap.add_argument("--channel", default=None,
                    help="channel profile: 1 = science, 3 = biography "
                         "(each keeps its own folders, so nothing crosses)")
    args = ap.parse_args()

    # switch the whole run onto one channel's folders before touching them
    prof = channel_profiles.profile(args.channel)
    CONTENT, WORK, OUT = prof["content"], prof["work"], prof["out"]
    channel_profiles.ensure(prof)

    scripts = sorted(CONTENT.glob("*.json"))
    if args.list:
        print(f"channel {prof['channel']} ({prof['label']}) -> {CONTENT.name}/"
              f"  out={OUT.name}/")
        for s in scripts:
            d = json.loads(s.read_text(encoding="utf-8"))
            done = (OUT / f"{d['slug']}.mp4").exists()
            print(f"  {'DONE ' if done else 'QUEUE'} {d['slug']:34s} {d['title'][:50]}")
        return 0

    todo = []
    if args.render:
        todo = [Path(args.render)]
    elif args.batch:
        wanted = None if args.only.strip().lower() == "all" else set(
            args.only.split())
        for s in scripts:
            d = json.loads(s.read_text(encoding="utf-8"))
            if wanted is not None and d["slug"] not in wanted:
                continue
            if not (OUT / f"{d['slug']}.mp4").exists():
                todo.append(s)
        if wanted is not None:
            missing = wanted - {json.loads(p.read_text(encoding="utf-8"))["slug"]
                                for p in scripts}
            if missing:
                print(f"unknown slugs: {sorted(missing)}")
                return 2
    else:
        ap.print_help()
        return 1

    failures = 0
    for path in todo:
        script = json.loads(path.read_text(encoding="utf-8"))
        orient = script.get("orientation", "landscape")
        print(f"\n== {script['slug']} ({orient}, {len(script['scenes'])} scenes)")
        try:
            build(script, WORK / script["slug"], orient)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    print(f"\nrendered {len(todo)-failures}/{len(todo)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
