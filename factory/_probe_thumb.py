# -*- coding: utf-8 -*-
"""Probe: can we set a custom thumbnail now, and if not, why?"""
import json
from pathlib import Path

from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

YT_AUTH = Path(r"C:\Users\USER\Desktop\chess-repo\yt_auth")
SCOPES = ["https://www.googleapis.com/auth/youtube"]

d = json.loads((YT_AUTH / "sci_token.json").read_text(encoding="utf-8"))
c = Credentials(token=d.get("access_token"), refresh_token=d.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=d.get("client_id"), client_secret=d.get("client_secret"),
                scopes=SCOPES)
if c.expired or not c.token:
    from google.auth.transport.requests import Request
    c.refresh(Request())
yt = build("youtube", "v3", credentials=c, cache_discovery=False)

vid = "9_sxoiuSo78"          # cold_short, live on the science channel
thumb = Path(r"C:\Users\USER\Desktop\chess-repo\factory\out\cold_short.jpg")

try:
    yt.thumbnails().set(
        videoId=vid,
        media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg"),
    ).execute()
    print("OK: thumbnail set accepted for", vid)
except HttpError as exc:
    print("HttpError", exc.resp.status)
    try:
        body = json.loads(exc.content.decode())
        print(json.dumps(body, indent=2, ensure_ascii=False))
    except Exception:
        print(exc.content[:500])
except Exception as exc:
    print(type(exc).__name__, exc)
