# -*- coding: utf-8 -*-
"""One word from the owner and the whole handover fires.

    python _confirm_and_upload.py

Guards: every one of the six fresh renders must exist (the stale ones
were deleted before the re-render, so existence == freshness).  Then:
  1. copies the six mp4s + six jpgs into the desktop sample folder
  2. deletes the old no-subtitle beethoven pair from the channel
  3. uploads the fresh pair through upload.py (daily cap respected)
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out_bio"
TOKEN = HERE.parent / "yt_auth" / "bio_token.json"
LEDGER = HERE / "state" / "uploaded_bio.json"
ROOT = Path.home() / "Desktop" / "\u062e\u062e\u062e\u06a9\u06a9\u06a9\u062e"
OLD_PAIR = ("2NaZvvbvVCM", "Sy4fdTWUGDw")
SLUGS = ("beethoven", "beethoven_short", "curie", "curie_short",
         "davinci", "davinci_short")


def bio_folder() -> Path:
    for d in ROOT.iterdir():
        if d.is_dir() and ("\u0632\u0646\u062f" in d.name or "bio" in d.name.lower()):
            return d
    raise SystemExit(f"bio sample folder not found under {ROOT}")


def fresh_files() -> list[Path]:
    missing = [f"{s}.mp4" for s in SLUGS if not (OUT / f"{s}.mp4").exists()]
    if missing:
        raise SystemExit(f"renders not ready yet: {missing} - nothing done")
    return [OUT / f"{s}.mp4" for s in SLUGS]


def access_token() -> str:
    data = json.loads(TOKEN.read_text(encoding="utf-8"))
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": data["refresh_token"],
        "client_id": data["client_id"],
        "client_secret": data["client_secret"],
    }).encode()
    tok = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=body)))
    return tok["access_token"]


def delete_live(video_ids: tuple[str, ...]) -> None:
    at = access_token()
    for vid in video_ids:
        req = urllib.request.Request(
            f"https://www.googleapis.com/youtube/v3/videos"
            f"?id={vid}&access_token={at}", method="DELETE")
        try:
            urllib.request.urlopen(req)
            print(f"  removed old video {vid}")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                print(f"  {vid} already gone")
            else:
                raise


def purge_ledger(video_ids: tuple[str, ...]) -> None:
    """Drop the dead pair's ledger entries.

    upload.py also dedupes by file name - without this purge the fresh
    render of the same slug would be skipped as a duplicate even though
    its video is already off the channel.
    """
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    before = len(data.get("uploaded", {}))
    data["uploaded"] = {k: v for k, v in data.get("uploaded", {}).items()
                        if v.get("videoId") not in video_ids}
    after = len(data["uploaded"])
    if after != before:
        LEDGER.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                          encoding="utf-8")
        print(f"  ledger: {before - after} stale entries dropped")


def main() -> int:
    fresh_files()                      # guard first - nothing moves on stale
    dst = bio_folder()
    for s in SLUGS:
        shutil.copy2(OUT / f"{s}.mp4", dst / f"{s}.mp4")
        shutil.copy2(OUT / f"{s}.jpg", dst / f"{s}.jpg")
    print(f"samples updated -> {dst}")

    delete_live(OLD_PAIR)
    purge_ledger(OLD_PAIR)

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["YT3_TOKEN_JSON"] = TOKEN.read_text(encoding="utf-8")
    print("uploading the fresh beethoven pair ...")
    res = subprocess.run(
        [sys.executable, str(HERE / "upload.py"),
         "--channel", "3", "--only", "beethoven beethoven_short"],
        cwd=HERE, env=env)
    print("done - curie and davinci go out through the 10:00 daily runs")
    return res.returncode


if __name__ == "__main__":
    raise SystemExit(main())
