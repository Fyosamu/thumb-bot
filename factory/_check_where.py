# -*- coding: utf-8 -*-
"""Which channel do the queued/old video IDs actually live on?"""
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

YT_AUTH = Path(r"C:\Users\USER\Desktop\chess-repo\yt_auth")
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CH = {
    "UCLN6rloxaP2BipjIQ2xLovQ": "secret_key/akhob59",
    "UCnaDonxf6T9QMIXM8H2HfPA": "Dazai/hkay7645",
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

ids = ["bxkMsYKTE8w", "lTNtp8OoUNU", "DTtvZvvnCcQ", "fgA14YPMaDg",
       "ji0DfdlQ2TU", "O7mpBkf7N_8"]
r = yt.videos().list(part="snippet,status", id=",".join(ids)).execute()
for it in r.get("items", []):
    s = it["snippet"]
    print(f"{it['id']} | {CH.get(s['channelId'], s['channelId'])} "
          f"| {s['publishedAt'][:16]} | {s['title'][:52]} "
          f"| {it['status'].get('privacyStatus')}")
missing = set(ids) - {it["id"] for it in r.get("items", [])}
if missing:
    print("not found / deleted:", missing)

pl = yt.channels().list(part="contentDetails", mine=True).execute()[
    "items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
resp = yt.playlistItems().list(part="snippet", playlistId=pl,
                                maxResults=3).execute()
print("--- snippet keys:",
      sorted(resp["items"][0]["snippet"].keys()))
