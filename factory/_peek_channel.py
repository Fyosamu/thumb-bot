# -*- coding: utf-8 -*-
"""Refresh bio_token and list the channel's uploads, to eyeball which
channel the token actually belongs to."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

p = Path(r"C:\Users\USER\Desktop\chess-repo\yt_auth\bio_token.json")
d = json.loads(p.read_text(encoding="utf-8"))
body = urllib.parse.urlencode({
    "grant_type": "refresh_token",
    "refresh_token": d["refresh_token"],
    "client_id": d["client_id"],
    "client_secret": d["client_secret"],
}).encode()
tok = json.load(urllib.request.urlopen(urllib.request.Request(
    "https://oauth2.googleapis.com/token", data=body)))
at = tok["access_token"]


def api(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(
        url, headers={"Authorization": "Bearer " + at})))


cid = d.get("channel_id") or "UCpDA-SRN7EFwd8VfpIcRztQ"
ch = api("https://www.googleapis.com/youtube/v3/channels"
         "?part=contentDetails,snippet&id=" + cid)
item = ch["items"][0]
print("channel:", item["snippet"]["title"], "|", item["id"])
pl = item["contentDetails"]["relatedPlaylists"]["uploads"]
its = api("https://www.googleapis.com/youtube/v3/playlistItems"
          "?part=snippet&playlistId=" + pl + "&maxResults=5")
for i in its.get("items", []):
    print("-", i["snippet"]["publishedAt"][:10], "|", i["snippet"]["title"])
