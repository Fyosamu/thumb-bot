# -*- coding: utf-8 -*-
"""Mint a YouTube OAuth token for one channel and file it like the others.

    python get_token.py 3 bio       # channel 3, saves yt_auth/bio_token.json
    python get_token.py 1 sci       # channel 1, saves yt_auth/sci_token.json

A browser window opens; sign in with THE Google account that owns that
channel. The client id/secret are reused from any existing token file, so
no console setup is needed. After the redirect lands on localhost the code
exchanges it for a refresh token and asks YouTube which channel the account
actually owns - that gets written into the file so no token can silently
belong to the wrong channel.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

YT_AUTH = Path(r"C:\Users\USER\Desktop\chess-repo\yt_auth")
SCOPES = ["https://www.googleapis.com/auth/youtube"]
# label used by daily_local.py for this channel's token file
TOKENS = {"1": "sci", "2": "chess", "3": "bio", "4": "pd"}


def template_client() -> dict:
    for name in ("chess_token.json", "sci_token.json", "yt_token.json"):
        p = YT_AUTH / name
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("client_id"):
                return {"client_id": d["client_id"],
                        "client_secret": d["client_secret"]}
    raise SystemExit("no existing token file carries a client_id; "
                     "cannot reuse the app credentials")


def main() -> int:
    key = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    label = (sys.argv[2] if len(sys.argv) > 2 else TOKENS.get(key, "")).strip()
    if key not in TOKENS or not label:
        raise SystemExit("usage: python get_token.py <1|2|3|4> <label>")

    from google_auth_oauthlib.flow import InstalledAppFlow

    tpl = template_client()
    flow = InstalledAppFlow.from_client_config(
        {"installed": {**tpl, "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                       "token_uri": "https://oauth2.googleapis.com/token",
                       "redirect_uris": ["http://localhost"]}}, SCOPES)
    creds = flow.run_local_server(port=8090, open_browser=True)

    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    ch = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
    out = YT_AUTH / f"{label}_token.json"
    out.write_text(json.dumps({
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": tpl["client_id"],
        "client_secret": tpl["client_secret"],
        "token_uri": "https://oauth2.googleapis.com/token",
        "scope": " ".join(SCOPES),
        "obtained": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "channel": ch["id"],
        "channel_title": ch["snippet"]["title"],
    }, indent=2), encoding="utf-8")
    print(f"saved {out}")
    print(f"channel: {ch['snippet']['title']} ({ch['id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
