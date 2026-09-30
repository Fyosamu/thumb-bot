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
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content"          # script JSONs live here
WORK = HERE / "work"                # per-video scratch space
OUT = HERE / "out"                  # finished mp4s
for d in (CONTENT, WORK, OUT):
    d.mkdir(parents=True, exist_ok=True)

FFMPEG = shutil.which("ffmpeg") or str(
    Path(r"C:\Users\USER\AppData\Local\Microsoft\WinGet\Packages"
         r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
         r"\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"))
FFPROBE = shutil.which("ffprobe") or str(Path(FFMPEG).with_name("ffprobe.exe"))

PEXELS_KEY = os.environ.get(
    "PEXELS_KEY",
    "DlTa4XKMzuGCvBy2bTTfvul2JP18DPM1LXYs4wHyHhRnrLqfJ9i55sm8")


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
    """Download one Pexels clip per scene, sized for the target orientation."""
    import requests

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
        r = requests.get("https://api.pexels.com/videos/search", params=params,
                         headers={"Authorization": PEXELS_KEY}, timeout=30)
        r.raise_for_status()
        videos = r.json().get("videos", [])
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

        with requests.get(chosen["link"], stream=True, timeout=120) as dl:
            dl.raise_for_status()
            with dest.open("wb") as fh:
                for chunk in dl.iter_content(1 << 20):
                    fh.write(chunk)
        clips.append(dest)
    return clips


def make_tts(script: dict, folder: Path, voice: str) -> list[Path]:
    """One mp3 per scene; returns them in scene order."""
    import asyncio

    import edge_tts

    folder.mkdir(parents=True, exist_ok=True)
    outs: list[Path] = []

    async def synth(text: str, dest: Path) -> None:
        if dest.exists() and dest.stat().st_size > 1000:
            return
        await edge_tts.Communicate(text, voice, rate="-5%").save(str(dest))

    async def main() -> None:
        for i, scene in enumerate(script["scenes"]):
            dest = folder / f"voice{i:02d}.mp3"
            await synth(scene["narration"], dest)
            outs.append(dest)

    asyncio.run(main())
    return outs


def build(script: dict, work: Path, orientation: str) -> Path:
    vw, vh = (1920, 1080) if orientation == "landscape" else (1080, 1920)

    print("  [1/4] tts (edge-tts, free)")
    voices = make_tts(script, work / "voice",
                      script.get("voice", "en-US-AvaMultilingualNeural"))
    durs = [duration_of(v) for v in voices]
    print(f"        {len(voices)} segments, {sum(durs):.1f}s total")

    print("  [2/4] stock footage (pexels, free)")
    clips = resolve_assets(script, work / "clips", orientation)

    print("  [3/4] assemble (ffmpeg)")
    parts_dir = work / "parts"
    parts_dir.mkdir(exist_ok=True)
    parts: list[Path] = []
    for i, (clip, dur, voice) in enumerate(zip(clips, durs, voices)):
        part = parts_dir / f"part{i:02d}.mp4"
        # scale/crop to target, trim to narration length, carry that scene's audio
        vf = (f"scale={vw}:{vh}:force_original_aspect_ratio=increase,"
              f"crop={vw}:{vh},fps=30,setsar=1")
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

    print("  [4/4] thumbnail (PIL)")
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


def make_thumbnail(script: dict, dest: Path, vw: int, vh: int) -> Path:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import requests

    bg_url = script.get("thumb_stock") or script["scenes"][0]["stock"]
    r = requests.get("https://api.pexels.com/v1/search",
                     params={"query": bg_url, "per_page": 1},
                     headers={"Authorization": PEXELS_KEY}, timeout=30)
    photo = None
    if r.ok and r.json().get("photos"):
        src = r.json()["photos"][0]["src"]["large2x"]
        img_r = requests.get(src, timeout=60)
        if img_r.ok:
            tmp = dest.with_suffix(".src.jpg")
            tmp.write_bytes(img_r.content)
            photo = Image.open(tmp).convert("RGB")

    if photo is None:
        photo = Image.new("RGB", (vw, vh), (18, 18, 24))
    # cover-fit
    scale = max(vw / photo.width, vh / photo.height)
    photo = photo.resize((int(photo.width * scale), int(photo.height * scale)))
    photo = photo.crop(((photo.width - vw) // 2, (photo.height - vh) // 2,
                        (photo.width - vw) // 2 + vw,
                        (photo.height - vh) // 2 + vh))
    photo = photo.filter(ImageFilter.GaussianBlur(2))

    draw = ImageDraw.Draw(photo, "RGBA")
    draw.rectangle([0, int(vh * 0.55), vw, vh], fill=(0, 0, 0, 150))

    text = script.get("thumb_text") or script["title"]
    font_size = int(vh * (0.13 if len(text) < 34 else 0.105))
    font = None
    for fp in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if Path(fp).exists():
            font = ImageFont.truetype(fp, font_size)
            break
    if font is None:
        font = ImageFont.load_default()

    lines = textwrap.wrap(text.upper(), width=18)[:3]
    y = int(vh * 0.60)
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (vw - w) / 2
        draw.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0, 230))
        draw.text((x, y), line, font=font, fill=(255, 214, 10, 255))
        y += int(font_size * 1.12)
    photo.save(dest, quality=93)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render")
    ap.add_argument("--batch", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="",
                    help="space-separated slugs to render (or 'all'); skips "
                         "anything already sitting in out/")
    args = ap.parse_args()

    scripts = sorted(CONTENT.glob("*.json"))
    if args.list:
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
