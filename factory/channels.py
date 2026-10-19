# -*- coding: utf-8 -*-
"""One profile per YouTube channel this bot publishes to.

Channel 1 (science) and channel 3 (biography) are deliberately kept in
completely separate script folders, render folders and ledgers, so a
biography episode can never be picked up by a science job, rendered into
a science folder, or uploaded to the science channel.  Each profile also
names the repo secret that carries its own OAuth token - there is no way
to cross the two.
"""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = HERE / "state"


def _state(name: str) -> Path:
    return STATE / name


# Anything the three tools (factory / pick / upload) need to know about a
# channel lives here.  Adding a channel means adding one entry.
PROFILES: dict[str, dict] = {
    "1": {
        "key": "1_science",
        "label": "science",
        "content": HERE / "content",
        "out": HERE / "out",
        "work": HERE / "work",
        "cursor": _state("cursor.json"),
        "manifest": _state("uploaded.json"),
        "count": _state("upload_count.json"),
        "token_used": _state("token_used.json"),
        "token_env": "YT1_TOKEN_JSON",
        "category": "27",          # Education
        "cron": "30 9 * * *",
        # one long plus its Short a day, spread six hours apart
        "daily_cap": 1,
        "spacing_hours": 6,
    },
    "2": {
        "key": "2_chess",
        "label": "chess",
        "content": HERE / "content_chess",
        "out": HERE / "out_chess",
        "work": HERE / "work_chess",
        "cursor": _state("cursor_chess.json"),
        "manifest": _state("uploaded_chess.json"),
        "count": _state("upload_count_chess.json"),
        "token_used": _state("token_used_chess.json"),
        "token_env": "YT2_TOKEN_JSON",
        "category": "27",          # Education
        "cron": "30 8 * * *",      # 08:30 UTC = 11:00 Tehran, before the others
        # one long plus its Short a day, six hours apart so both land
        # inside the same day - the owner's pace is one pair per channel
        "daily_cap": 1,
        "spacing_hours": 6,
    },
    "3": {
        "key": "3_biography",
        "label": "biography",
        "content": HERE / "content_bio",
        "out": HERE / "out_bio",
        "work": HERE / "work_bio",
        "cursor": _state("cursor_bio.json"),
        "manifest": _state("uploaded_bio.json"),
        "count": _state("upload_count_bio.json"),
        "token_used": _state("token_used_bio.json"),
        "token_env": "YT3_TOKEN_JSON",
        "category": "24",          # Entertainment
        "cron": "0 10 * * *",
        # one long plus its Short a day, like the other two channels
        "daily_cap": 1,
        "spacing_hours": 6,
    },
    # channel 4 = personal development: projects/pdrip/robot.py discovers a
    # Persian source video, translates it, writes the script HERE, renders
    # and uploads through the exact same machinery (upload.py + manifest +
    # daily cap).  Its own token env: YT4_TOKEN_JSON (repo secret PD_TOKEN_JSON).
    "4": {
        "key": "4_personaldev",
        "label": "personaldev",
        "content": HERE / "content_pd",
        "out": HERE / "out_pd",
        "work": HERE / "work_pd",
        "cursor": _state("cursor_pd.json"),
        "manifest": _state("uploaded_pd.json"),
        "count": _state("upload_count_pd.json"),
        "token_used": _state("token_used_pd.json"),
        "token_env": "YT4_TOKEN_JSON",
        "category": "27",          # Education
        "cron": "30 14 * * *",
        # one translated long a day, forever - the robot never stops
        "daily_cap": 1,
        "spacing_hours": 6,
    },
}


def _register_multichan() -> None:
    """Channels 5..104 live in projects/multichan/channels.json (generated
    by gen_channels.py).  Registering them here means factory/upload/get_token
    treat a personal-development side channel exactly like the originals -
    its own folders, its own ledger, its own YT<n>_TOKEN_JSON secret."""
    import json

    reg = HERE.parent / "projects" / "multichan" / "channels.json"
    if not reg.exists():
        return
    for e in json.loads(reg.read_text(encoding="utf-8")).get("channels", []):
        cid = str(e["id"])
        PROFILES[cid] = {
            "key": f"{cid}_{e['slug']}",
            "label": e["slug"],
            "content": HERE / f"content_m{cid}",
            "out": HERE / f"out_m{cid}",
            "work": HERE / f"work_m{cid}",
            "cursor": _state(f"cursor_m{cid}.json"),
            "manifest": _state(f"uploaded_m{cid}.json"),
            "count": _state(f"upload_count_m{cid}.json"),
            "token_used": _state(f"token_used_m{cid}.json"),
            "token_env": f"YT{cid}_TOKEN_JSON",
            "category": e.get("yt_category", "27"),
            "cron": e.get("cron", "0 13 * * *"),
            "daily_cap": 1,
            "spacing_hours": 6,
        }


_register_multichan()


def profile(channel: str | None = None) -> dict:
    """Resolve a channel number into its paths, token and defaults."""
    key = str(channel or os.environ.get("YT_CHANNEL") or "1").strip()
    if key not in PROFILES:
        raise SystemExit(
            f"unknown channel {key!r}; expected one of {sorted(PROFILES)}")
    p = dict(PROFILES[key])
    p["channel"] = key
    return p


def ensure(p: dict) -> None:
    """Create the folders a profile expects to find."""
    for k in ("content", "out", "work"):
        Path(p[k]).mkdir(parents=True, exist_ok=True)
    Path(p["manifest"]).parent.mkdir(parents=True, exist_ok=True)
