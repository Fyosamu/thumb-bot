# -*- coding: utf-8 -*-
"""Mint bio_token.json without opening the system browser.

Prints the consent URL so it can be opened in a controlled browser; the
local server on :8090 still catches the redirect.  Same client id as the
other tokens; prompt=consent guarantees a refresh_token comes back.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from get_token import template_client  # noqa: E402

YT_AUTH = HERE.parent / "yt_auth"
SCOPES = ["https://www.googleapis.com/auth/youtube"]

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

flow = InstalledAppFlow.from_client_config(
    {"installed": {**template_client(),
                   "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                   "token_uri": "https://oauth2.googleapis.com/token",
                   "redirect_uris": ["http://localhost"]}}, SCOPES)
# run_local_server mints the real URL itself (redirect_uri + state live
# there); a hand-built URL is missing redirect_uri and Google rejects it.
creds = flow.run_local_server(port=8090, open_browser=True,
                              authorization_prompt_message="AUTH_URL {url}",
                              success_message="", prompt="consent")

if not creds.refresh_token:
    raise SystemExit("no refresh_token returned; rerun the script")

# get_token's template_client already holds the id/secret of the other
# tokens - flow.client_config is not guaranteed to keep its wrapper.
tc = template_client()
out = YT_AUTH / "bio_token.json"


def save(channel_id=None, channel_title=None):
    out.write_text(json.dumps({
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": tc["client_id"],
        "client_secret": tc["client_secret"],
        "token_uri": "https://oauth2.googleapis.com/token",
        "scope": " ".join(SCOPES),
        "obtained": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "channel": channel_id,
        "channel_title": channel_title,
    }, indent=2), encoding="utf-8")


save()  # the token lands first; a dead channel lookup can no longer eat it
print(f"saved {out}")

try:
    from googleapiclient.discovery import build  # noqa: E402
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    ch = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
    save(ch["id"], ch["snippet"]["title"])
    print(f"channel: {ch['snippet']['title']} ({ch['id']})")
except Exception as exc:  # token is already safe on disk
    print(f"channel lookup failed ({exc}); token still saved")
