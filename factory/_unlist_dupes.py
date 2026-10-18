# -*- coding: utf-8 -*-
"""Unlist the four accidental duplicate uploads on the science channel.

Unlisted, not deleted — everything stays recoverable. The kept copy is always
the one recorded in state/uploaded.json (the channel manifest).
"""
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

YT_AUTH = Path(r"C:\Users\USER\Desktop\chess-repo\yt_auth")
SCOPES = ["https://www.googleapis.com/auth/youtube"]

# videoId -> reason
DUPES = {
    "GDsQWSsaug4": "focus.mp4 uploaded twice today (kept: oruy0iudrPM)",
    "lTNtp8OoUNU": "age long from old factory today (kept: NKWflZ8Fpk4, 9/30)",
    "DTtvZvvnCcQ": "attention long from old factory today (kept: -pWD5Q9detQ, 10/2)",
    "-nBf7p6IDXw": "cold long uploaded twice on 10/12 (kept: 040SAbfctFk)",
}

d = json.loads((YT_AUTH / "sci_token.json").read_text(encoding="utf-8"))
c = Credentials(token=d.get("access_token"), refresh_token=d.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=d.get("client_id"), client_secret=d.get("client_secret"),
                scopes=SCOPES)
if c.expired or not c.token:
    from google.auth.transport.requests import Request
    c.refresh(Request())
yt = build("youtube", "v3", credentials=c, cache_discovery=False)

for vid, why in DUPES.items():
    try:
        yt.videos().update(
            part="status",
            body={"id": vid, "status": {"privacyStatus": "unlisted"}},
        ).execute()
        print(f"unlisted {vid}  <- {why}")
    except Exception as exc:
        print(f"FAILED   {vid}: {exc}")
