# -*- coding: utf-8 -*-
"""Print which YouTube channel + email each token file belongs to."""
import json
from pathlib import Path

YT_AUTH = Path(r"C:\Users\USER\Desktop\chess-repo\yt_auth")

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube"]

for name in ("chess_token.json", "sci_token.json", "yt_token.json", "bio_token.json"):
    p = YT_AUTH / name
    if not p.exists():
        print(f"{name}: MISSING")
        continue
    data = json.loads(p.read_text(encoding="utf-8"))
    c = Credentials(token=data.get("access_token"),
                    refresh_token=data.get("refresh_token"),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=data.get("client_id"),
                    client_secret=data.get("client_secret"),
                    scopes=SCOPES)
    try:
        if c.expired or not c.token:
            from google.auth.transport.requests import Request
            c.refresh(Request())
        yt = build("youtube", "v3", credentials=c, cache_discovery=False)
        ch = yt.channels().list(part="snippet,statistics", mine=True).execute()
        items = ch.get("items", [])
        if items:
            s = items[0]["snippet"]
            st = items[0]["statistics"]
            print(f"{name}: title={s['title']!r} customUrl={s.get('customUrl','')} "
                  f"subs={st.get('subscriberCount')} videos={st.get('videoCount')} "
                  f"country={s.get('country','')}")
        else:
            print(f"{name}: token valid but NO channel bound")
    except Exception as exc:
        print(f"{name}: ERROR {type(exc).__name__}: {exc}")
