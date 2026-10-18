# -*- coding: utf-8 -*-
"""Full duplicate-title audit of the science channel (akhob59/secret_key)."""
import json
from collections import defaultdict
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

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

pl = yt.channels().list(part="contentDetails", mine=True).execute()[
    "items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

rows = []
tok = None
while True:
    kw = {"playlistId": pl, "part": "snippet", "maxResults": 50}
    if tok:
        kw["pageToken"] = tok
    resp = yt.playlistItems().list(**kw).execute()
    for it in resp["items"]:
        s = it["snippet"]
        vid = s.get("resourceId", {}).get("videoId")
        rows.append((vid, s.get("title", ""), s.get("publishedAt", "")))
    tok = resp.get("nextPageToken")
    if not tok:
        break

print(f"total videos on channel: {len(rows)}")
by_title = defaultdict(list)
for vid, t, pa in rows:
    by_title[t.replace(" #Shorts", "").strip().lower()].append((vid, pa, t))

print("\n--- titles with more than one video:")
for t, lst in sorted(by_title.items()):
    if len(lst) > 1:
        print(f"\n  x{len(lst)}: {t}")
        for vid, pa, orig in lst:
            print(f"      {pa[:16]}  {vid}  {'[short]' if '#Shorts' in orig else '[long]'}")
