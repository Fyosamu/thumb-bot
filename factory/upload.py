# -*- coding: utf-8 -*-
"""Upload what the runner just rendered, then record it in the repo state.

Runs on GitHub Actions, so nothing travels through the owner's machine:

    YT_TOKEN_JSON   OAuth token as a JSON string (repo secret)
    PEXELS_KEY      unused here, needed by factory.py on the same job

Dedupe is sha256 against state/uploaded.json, the same rule the local
publish.py uses, so a video can never be published twice from either place.

Usage:
    python upload.py                 # everything pending, up to the daily cap
    python upload.py --dry-run
    python upload.py --only age age_short
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import channels as channel_profiles

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
CONTENT = HERE / "content"
STATE = HERE / "state"
MANIFEST = STATE / "uploaded.json"
COUNT = STATE / "upload_count.json"

# filled in per channel by main() from channels.PROFILES
TOKEN_ENV = "YT1_TOKEN_JSON"
TOKEN_USED = STATE / "token_used.json"
DEFAULT_CATEGORY = "27"

DAILY_CAP = 4
SPACING_HOURS = 6
SCOPES = ["https://www.googleapis.com/auth/youtube"]
# 27=Education, 24=Entertainment
CATEGORY = {"bio": "24", "biography": "24"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(p: Path, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def uploads_today() -> int:
    d = load(COUNT, {})
    return int(d.get("count", 0)) if d.get("date") == today() else 0


def publish_slot() -> str | None:
    n = uploads_today()
    if n <= 0:
        return None
    t = datetime.now(timezone.utc) + timedelta(hours=SPACING_HOURS * n)
    return t.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def creds():
    from google.oauth2.credentials import Credentials
    # each channel carries its own token; never fall back to another's
    raw = os.environ.get(TOKEN_ENV, "").strip()
    if not raw:
        raise SystemExit(f"{TOKEN_ENV} is not set - this channel cannot "
                         "publish without its own token")
    data = json.loads(raw)
    c = Credentials(token=data.get("access_token"),
                    refresh_token=data.get("refresh_token"),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=data.get("client_id"),
                    client_secret=data.get("client_secret"),
                    scopes=SCOPES)
    if c.expired or not c.token:
        from google.auth.transport.requests import Request
        c.refresh(Request())
        data["access_token"] = c.token
        save(TOKEN_USED, {k: data.get(k) for k in
                          ("client_id", "refresh_token")})
    return c


def category_for(slug: str) -> str:
    f = slug.lower()
    if "bio" in f or "trump" in f:
        return "24"
    return CATEGORY.get(f.split("_")[0], DEFAULT_CATEGORY)


def collect(uploaded: dict) -> tuple[list[dict], list[str]]:
    pending, dup = [], []
    # a re-render produces identical content at a different hash, so the
    # ledger is also checked by file name - a slug on the channel stays on
    # the channel no matter how many times it is rebuilt
    by_name = {u.get("file") for u in uploaded.values()}
    for video in sorted(OUT.glob("*.mp4")):
        meta = CONTENT / f"{video.stem}.json"
        if not meta.exists():
            continue
        d = json.loads(meta.read_text(encoding="utf-8"))
        digest = sha256(video)
        if digest in uploaded or video.name in by_name:
            dup.append(video.stem)
            continue
        pending.append({"slug": video.stem, "path": video, "meta": d,
                        "sha256": digest})
    return pending, dup


def main() -> int:
    global OUT, CONTENT, STATE, MANIFEST, COUNT
    global TOKEN_ENV, TOKEN_USED, DEFAULT_CATEGORY
    global DAILY_CAP, SPACING_HOURS
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--channel", default=None,
                    help="channel profile: 1 = science, 3 = biography - "
                         "separate folders, separate ledger, separate token")
    args = ap.parse_args()

    # park this run on exactly one channel's folders and token
    prof = channel_profiles.profile(args.channel)
    OUT, CONTENT = prof["out"], prof["content"]
    STATE = Path(prof["manifest"]).parent
    MANIFEST, COUNT = prof["manifest"], prof["count"]
    TOKEN_ENV, TOKEN_USED = prof["token_env"], prof["token_used"]
    DEFAULT_CATEGORY = prof["category"]
    DAILY_CAP = int(prof.get("daily_cap", 4))
    SPACING_HOURS = float(prof.get("spacing_hours", 6))
    channel_profiles.ensure(prof)

    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    manifest = load(MANIFEST, {"uploaded": {}})
    uploaded = manifest["uploaded"]
    pending, dup = collect(uploaded)
    print(f"channel {prof['channel']} ({prof['label']}) -> {OUT.name}/ "
          f"token {TOKEN_ENV}")
    if args.only:
        want = set(args.only.split())
        pending = [p for p in pending if p["slug"] in want]

    room = max(0, DAILY_CAP - uploads_today())
    print(f"pending {len(pending)} | dup {len(dup)} | cap {room}/{DAILY_CAP} left")
    for s in dup:
        print("  SKIP dup ", s)
    if not pending or room == 0 or args.dry_run:
        for p in pending:
            print("  PENDING  ", p["slug"], "|", p["meta"].get("title", "")[:60])
        return 0

    yt = build("youtube", "v3", credentials=creds(), cache_discovery=False)
    done = 0
    for item in pending:
        if done >= room:
            print("daily cap reached, stopping")
            break
        slug, meta, path = item["slug"], item["meta"], item["path"]
        title = str(meta.get("title", slug))[:100]
        body = {
            "snippet": {
                "title": title,
                "description": str(meta.get("description", ""))[:4900],
                "tags": list(meta.get("tags", []))[:40],
                "categoryId": category_for(slug),
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {"privacyStatus": "public",
                       "selfDeclaredMadeForKids": False,
                       "embeddable": True,
                       "publicStatsViewable": True},
        }
        slot = publish_slot()
        if slot:
            body["status"].update(privacyStatus="private", publishAt=slot)
            print(f"  {slug}: scheduled -> {slot}")

        print(f"  uploading {slug} ({path.stat().st_size/1e6:.1f} MB)...")
        media = MediaFileUpload(str(path), mimetype="video/mp4",
                                chunksize=8 * 1024 * 1024, resumable=True)
        req = yt.videos().insert(part="snippet,status", body=body,
                                 media_body=media, notifySubscribers=True)
        resp, attempt = None, 0
        while resp is None:
            try:
                st, resp = req.next_chunk()
                if st:
                    print(f"    {int(st.progress()*100)}%", end="\r", flush=True)
            except HttpError as exc:
                reason = ""
                try:
                    reason = json.loads(exc.content.decode())["error"] \
                        ["errors"][0].get("reason", "")
                except Exception:
                    pass
                if reason in ("uploadLimitExceeded", "quotaExceeded",
                              "forbidden", "authError", "badRequest"):
                    print(f"\n  {slug}: permanent failure {reason}")
                    break
                attempt += 1
                if attempt > 5:
                    raise
                time.sleep(min(60, 5 * attempt))
                media = MediaFileUpload(str(path), mimetype="video/mp4",
                                        chunksize=8 * 1024 * 1024,
                                        resumable=True)
                req = yt.videos().insert(part="snippet,status", body=body,
                                         media_body=media, notifySubscribers=True)
        if not resp:
            break

        vid = resp["id"]

        # record the upload before touching the thumbnail: any crash in there
        # must not lose the entry, or the next run pushes the same file twice
        uploaded[item["sha256"]] = {
            "videoId": vid, "url": f"https://youtu.be/{vid}",
            "title": title, "folder": "ci", "file": path.name,
            "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "size": path.stat().st_size,
        }
        save(MANIFEST, manifest)
        save(COUNT, {"date": today(), "count": uploads_today() + 1})

        thumb = OUT / f"{slug}.jpg"
        if thumb.exists():
            try:
                yt.thumbnails().set(
                    videoId=vid,
                    media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")
                ).execute()
            except Exception as exc:
                print(f"    thumbnail skipped ({exc})")

        print(f"  OK {slug} -> https://youtu.be/{vid}")
        done += 1

    print(f"\nuploaded {done}; state has {len(uploaded)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
