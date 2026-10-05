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
    },
}


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
