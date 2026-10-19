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
import time
from datetime import datetime, timezone
from pathlib import Path

YT_AUTH = Path(r"C:\Users\USER\Desktop\chess-repo\yt_auth")
SCOPES = ["https://www.googleapis.com/auth/youtube"]
# label used by daily_local.py for this channel's token file
TOKENS = {"1": "sci", "2": "chess", "3": "bio", "4": "pd"}


def template_client() -> dict:
    # fleet_client.json (projects/multichan era, project mindseries-fleet)
    # wins for NEW mints: it belongs to aryn82674's project, so its creator
    # can authorize it in testing mode without the old client's test-user
    # wall.  Existing tokens keep the client embedded in their own file.
    for name in ("fleet_client.json", "chess_token.json", "sci_token.json",
                 "yt_token.json"):
        p = YT_AUTH / name
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("client_id") and d.get("client_secret"):
                return {"client_id": d["client_id"],
                        "client_secret": d["client_secret"]}
    raise SystemExit("no existing token file carries a client_id; "
                     "cannot reuse the app credentials")


def main() -> int:
    key = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    # 1-4 keep their named labels; a multichan channel (5..104) files its
    # token as m<id>_token.json, which is exactly what the matrix job reads.
    if key not in TOKENS and (key.isdigit() and 5 <= int(key) <= 104):
        TOKENS[key] = f"m{key}"
    label = (sys.argv[2] if len(sys.argv) > 2 else TOKENS.get(key, "")).strip()
    if key not in TOKENS or not label:
        raise SystemExit("usage: python get_token.py <1|2|3|4> <label>"
                         "   |   python get_token.py <5..104>")

    from google_auth_oauthlib.flow import InstalledAppFlow

    tpl = template_client()
    flow = InstalledAppFlow.from_client_config(
        {"installed": {**tpl, "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                       "token_uri": "https://oauth2.googleapis.com/token",
                       "redirect_uris": ["http://localhost"]}}, SCOPES)
    creds = flow.run_local_server(port=8090, open_browser=True)

    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    items = yt.channels().list(part="snippet", mine=True).execute().get(
        "items", [])
    if not items:
        # a brand-new Google account has no YouTube channel yet - the
        # owner creates one in the browser window that is already open,
        # and this waits for it instead of crashing the OAuth session
        print("[wait] no YouTube channel on this account yet.")
        print("[wait] open youtube.com -> avatar -> Create a channel; "
              "polling up to 10 minutes...")
        for _ in range(40):
            time.sleep(15)
            items = yt.channels().list(part="snippet", mine=True).execute().get(
                "items", [])
            if items:
                break
        else:
            print("[wait] timed out - create the channel, then run this "
                  "command again (you are signed in, it is one click)")
            return 1
    ch = items[0]
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
    print()
    print(f"next, hand it to the runner:")
    print(f"  gh secret set YT{key}_TOKEN_JSON < {out}")
    print(f"  (then add {key} to projects/multichan/state/active_channels.json"
          " and push - the matrix wakes up)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
