# -*- coding: utf-8 -*-
"""Apply a multichan channel's identity on YouTube - title, description,
keywords and the 2560x1440 banner (pulled by URL from the public
`Fyosamu/brands` repo) - exactly once per channel.

    python set_brand.py --channel 47

Env must carry the OAuth token as YT47_TOKEN_JSON (the workflow writes it
there from secret YT47_TOKEN_JSON).  Idempotent and non-intrusive: the
first successful pass records state/branded_m47.json and every later run
reads that and stays quiet, so a manual tweak made in YouTube Studio is
never overwritten.  A failed pass records nothing and retries tomorrow.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACTORY = HERE.parent.parent / "factory"
sys.path.insert(0, str(FACTORY))

SCOPES = ["https://www.googleapis.com/auth/youtube"]
BRANDS_RAW = "https://raw.githubusercontent.com/Fyosamu/brands/main"


def registry(cid: str) -> dict | None:
    reg = HERE / "channels.json"
    for e in json.loads(reg.read_text(encoding="utf-8")).get("channels", []):
        if str(e["id"]) == str(cid):
            return e
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True)
    args = ap.parse_args()
    cid = str(args.channel).strip()

    marker = HERE / "state" / f"branded_m{cid}.json"
    if marker.exists():
        print(f"[brand] channel {cid} already branded - skipping")
        return 0

    token_env = f"YT{cid}_TOKEN_JSON"
    raw = os.environ.get(token_env, "").strip()
    if not raw:
        print(f"[brand] {token_env} not set - branding skipped")
        return 0

    entry = registry(cid)
    if not entry:
        print(f"[brand] channel {cid} not in channels.json - cannot brand")
        return 0

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    creds = Credentials.from_authorized_user_info(json.loads(raw),
                                                  scopes=SCOPES)
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    mine = yt.channels().list(part="snippet,brandingSettings",
                              mine=True).execute().get("items", [])
    if not mine:
        print("[brand] token owns no channel - check the account")
        return 1
    ch = mine[0]

    banner_url = f"{BRANDS_RAW}/{cid}_banner.jpg"
    body = {
        "id": ch["id"],
        "snippet": {
            "title": entry["name"],
            "description": entry["description"],
            # category stays whatever YouTube already has; the API refuses
            # assignable/false values on managed accounts
        },
        "brandingSettings": {
            "channel": {
                "title": entry["name"],
                "description": entry["description"],
                "keywords": (f"{entry['category_en']}, personal development, "
                             f"self improvement, {entry['slug']}, "
                             "mindset, daily motivation"),
            },
            "image": {"bannerExternalUrl": banner_url},
        },
    }

    # NOTE: youtube forbids part=brandingSettings alongside any other part
    # on channels.update ("branding_settings cannot be used with other
    # parts"), and part=snippet is not updatable at all for channels
    # (ERROR_PART_UNEXPECTED) - title/description/keywords live inside
    # brandingSettings.channel and go in this single call, banner too.
    try:
        yt.channels().update(part="brandingSettings", body={
            "id": ch["id"],
            "brandingSettings": body["brandingSettings"],
        }).execute()
    except HttpError as exc:
        # most often the banner URL being 404 (brands repo not pushed yet)
        # or an unverified new channel - record nothing, retry next wave
        print(f"[brand] update failed for channel {cid}: "
              f"{getattr(exc, 'resp', exc)}")
        print(getattr(exc, "content", b"").decode("utf-8", "replace")[:400])
        return 0

    # youtube accepts the call (200) yet can silently drop fields:
    # a personal-account channel keeps its title tied to the google
    # account name, and brand-new channels often ignore bannerExternalUrl
    # until they age / get phone-verified. read back, warn, keep going -
    # description + keywords do apply, and the account rename fixes the
    # title on its own.
    try:
        back = yt.channels().list(part="snippet,brandingSettings",
                                  id=ch["id"]).execute()
        item = (back.get("items") or [{}])[0]
        got_title = item.get("snippet", {}).get("title", "")
        got_img = (item.get("brandingSettings", {})
                   .get("image", {}).get("bannerExternalUrl", ""))
        if got_title != entry["name"]:
            print(f"[brand] NOTE: title still {got_title!r} - personal "
                  f"channel titles follow the google account name; "
                  f"rename the account to {entry['name']!r} to apply")
        if not got_img:
            print(f"[brand] NOTE: banner not applied yet for channel "
                  f"{cid} (new-channel lag) - daily cron will keep the "
                  f"rest; set it in Studio > Customization if it sticks")
    except HttpError as exc:
        print(f"[brand] readback failed: {getattr(exc, 'resp', exc)}")

    marker.write_text(json.dumps({
        "channel_id": ch["id"],
        "title": entry["name"],
        "banner": banner_url,
    }, indent=1), encoding="utf-8")
    print(f"[brand] set: {entry['name']} + banner for channel {cid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
