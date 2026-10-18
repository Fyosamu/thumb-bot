# -*- coding: utf-8 -*-
"""Set styled custom thumbnails on the live videos of a channel.

Usage:
    python _set_thumbs.py 1      # science   (sci_token)  - account must be
    python _set_thumbs.py 2      # chess     (chess_token)   verified in
    python _set_thumbs.py 3      # biography (bio_token)     YouTube Studio

Videos are matched to the script bank by exact title.  A video with no
local jpg gets one generated on the spot: chess renders the board fully
offline, science/bio fetch one stock photo through Pexels.  What has
already been set is remembered in state/thumbs_set_<channel>.json, so a
daily run only spends the small thumbnail quota on videos that still need
one.  YouTube answers 429 once the quota is spent; the run then stops and
picks up where it left off on the next day.
"""
import json
import re
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

HERE = Path(__file__).resolve().parent
YT_AUTH = HERE.parent / "yt_auth"
SCOPES = ["https://www.googleapis.com/auth/youtube"]
TOKENS = {"1": "sci_token.json", "2": "chess_token.json", "3": "bio_token.json"}
OUTS = {"1": HERE / "out", "2": HERE / "out_chess", "3": HERE / "out_bio"}
SCRIPTS = {"1": HERE / "content", "2": HERE / "content_chess",
           "3": HERE / "content_bio"}

ch = sys.argv[1] if len(sys.argv) > 1 else "2"

sys.path.insert(0, str(HERE))
import channels as channel_profiles  # noqa: E402

if ch == "2":
    import chess_factory as cf       # noqa: E402
    longs = sorted(p.stem for p in SCRIPTS[ch].glob("*.json")
                   if "_short" not in p.stem)
else:
    import factory as fac             # noqa: E402

data = json.loads((YT_AUTH / TOKENS[ch]).read_text(encoding="utf-8"))
creds = Credentials(
    token=data.get("access_token"), refresh_token=data.get("refresh_token"),
    token_uri="https://oauth2.googleapis.com/token",
    client_id=data.get("client_id"), client_secret=data.get("client_secret"),
    scopes=SCOPES)
if creds.expired or not creds.token:
    creds.refresh(Request())
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)


def ensure_jpg(slug: str) -> Path | None:
    jpg = OUTS[ch] / f"{slug}.jpg"
    if jpg.exists():
        return jpg
    js = SCRIPTS[ch] / f"{slug}.json"
    if not js.exists():
        return None
    script = json.loads(js.read_text(encoding="utf-8"))
    try:
        if ch == "2":
            stem = re.sub(r"_short\d*$", "", slug)
            part = longs.index(stem) + 1 if stem in longs else 0
            pz = script["puzzles"][0]
            if cf.is_short(slug):
                cf.make_thumb(script, pz, jpg, 1080, 1920, part)
            else:
                cf.make_thumb(script, pz, jpg, 1920, 1080, part)
        else:
            orient = script.get("orientation", "landscape")
            w, h = (1920, 1080) if orient == "landscape" else (1080, 1920)
            fac.make_thumbnail(script, jpg, w, h)
    except Exception as exc:  # noqa: BLE001
        print(f"  gen fail {slug}: {type(exc).__name__}: {exc}")
        return None
    return jpg


# title -> script, one pass over the bank (chess bank is big; runs offline)
title2slug: dict[str, str] = {}
for js in sorted(SCRIPTS[ch].glob("*.json")):
    head = json.loads(js.read_text(encoding="utf-8"))
    if head.get("title") and head.get("slug"):
        title2slug[str(head["title"]).strip()] = head["slug"]

uploads = yt.channels().list(part="contentDetails", mine=True).execute()
playlist = uploads["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

STATE = HERE / "state"
STATE.mkdir(exist_ok=True)
done_file = STATE / f"thumbs_set_{ch}.json"
done = (json.loads(done_file.read_text(encoding="utf-8"))
        if done_file.exists() else {})

set_count = no_local = 0
quota = False
token = None
while not quota:
    page = yt.playlistItems().list(
        part="snippet", playlistId=playlist, maxResults=50,
        pageToken=token).execute()
    for item in page["items"]:
        title = str(item["snippet"]["title"]).strip()
        vid = item["snippet"]["resourceId"]["videoId"]
        slug = title2slug.get(title)
        if slug is None or vid in done:
            no_local += 1
            continue
        jpg = ensure_jpg(slug)
        if jpg is None:
            no_local += 1
            continue
        try:
            yt.thumbnails().set(
                videoId=vid,
                media_body=MediaFileUpload(str(jpg), mimetype="image/jpeg"),
            ).execute()
            print(f"set {vid}  {title[:60]}")
            set_count += 1
            done[vid] = title
            done_file.write_text(json.dumps(done, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
        except HttpError as exc:
            print(f"FAIL {vid} {exc.resp.status} {str(exc.content)[:180]}")
            if exc.resp.status == 403:
                sys.exit("403: enable custom thumbnails "
                         "(YouTube Studio > Channel > Feature eligibility)")
            if exc.resp.status == 429:
                print("thumbnail quota hit - the rest continues on the next run")
                quota = True
                break
    if quota:
        break
    token = page.get("nextPageToken")
    if not token:
        break

print(f"done: {set_count} set, {no_local} skipped "
      "(no script, already set, or no local jpg)")
