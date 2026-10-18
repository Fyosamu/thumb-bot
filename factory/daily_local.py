# -*- coding: utf-8 -*-
"""Render and publish one episode per channel, with no human in the loop.

GitHub's runners are the intended host for this, but the repo cannot be
pushed from this machine until credentials exist, so Windows Task Scheduler
runs this instead.  It is the same sequence the CI workflow performs:

    pick -> render -> upload -> advance

The cursor only advances after a successful upload, so a failed day retries
the same episode rather than skipping it.  A channel with no token of its
own is skipped outright - it can never borrow another channel's identity.
"""
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import channels as channel_profiles

REPO = Path(__file__).resolve().parent.parent
FACTORY = REPO / "factory"
YT_AUTH = REPO / "yt_auth"
LOGS = REPO / "factory" / "state" / "logs"
# label, token file, renderer.  Chess scripts hold board positions
# (`puzzles`), not narration scenes, so they go through chess_factory.py -
# factory.py dies with KeyError: 'scenes' on them.
# the daily order is the owner's: chess first, then science, then biography
CHANNELS = {"2": ("chess", "chess_token.json", "chess_factory.py"),
            "1": ("science", "sci_token.json", "factory.py"),
            "3": ("bio", "bio_token.json", "factory.py")}


def run(args: list[str], env: dict) -> int:
    p = subprocess.run(args, cwd=REPO, env=env,
                       capture_output=True, text=True)
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    return p.returncode, out


def room_left(key: str) -> int:
    """Uploads still open for this channel today, per its own cap."""
    prof = channel_profiles.profile(key)
    cap = int(prof.get("daily_cap", 2))
    try:
        state = json.loads(Path(prof["count"]).read_text(encoding="utf-8"))
    except Exception:                                   # noqa: BLE001
        state = {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    used = int(state.get("count", 0)) if state.get("date") == today else 0
    return max(0, cap - used)


def _one_episode(key: str, env: dict, label: str, renderer: str) -> tuple[str, bool]:
    """Pick, render and upload one episode.  Returns (report, keep_going)."""
    rc, out = run([sys.executable, str(FACTORY / "pick.py"),
                   "next", "--channel", key], env)
    if rc != 0:
        return f"{label}: pick failed\n{out}", False
    # the last "[label] slug slug ..." line is the queue offer
    lines = [l for l in out.strip().splitlines() if l.strip().startswith("[")]
    slugs = lines[-1].split()[1:] if lines else []
    if not slugs or not slugs[0] or slugs[0].startswith("("):
        return f"{label}: queue empty - nothing left to publish", False

    rc, out = run([sys.executable, str(FACTORY / renderer),
                   "--batch", "--channel", key, "--only", " ".join(slugs)], env)
    if rc != 0:
        return f"{label}: render failed\n{out[-1500:]}", False

    rc, out = run([sys.executable, str(FACTORY / "upload.py"),
                   "--channel", key, "--only", " ".join(slugs)], env)
    if rc != 0:
        return f"{label}: upload failed\n{out[-1500:]}", False

    # the cursor only moves when every slug of this episode is actually on
    # the channel; a run cut short by the daily cap simply retries the rest
    manifest = json.loads(Path(channel_profiles.profile(key)["manifest"])
                          .read_text(encoding="utf-8"))
    files = {u.get("file") for u in manifest.get("uploaded", {}).values()}
    missing = [s for s in slugs if f"{s}.mp4" not in files]
    if missing:
        return (f"{label}: uploaded {len(slugs) - len(missing)}/{len(slugs)} "
                f"today, waiting on {', '.join(missing)}"), False

    run([sys.executable, str(FACTORY / "pick.py"),
         "advance", "--channel", key], env)
    return f"{label}: published {' + '.join(slugs)}", True


def do_channel(key: str) -> str:
    label, token_name, renderer = CHANNELS[key]
    token = YT_AUTH / token_name
    if not token.exists():
        return f"{label}: skipped - no token ({token_name})"

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    # each channel gets its own token in its own env var; never shared
    env[f"YT{key}_TOKEN_JSON"] = token.read_text(encoding="utf-8")

    # one pass per episode, but keep going until the channel's own daily cap
    # is full - that is what turns the queue into "N a day" on its own
    report: list[str] = []
    for _ in range(6):
        if room_left(key) <= 0:
            report.append(f"{label}: daily cap reached ({room_left(key)} left)")
            break
        line, keep_going = _one_episode(key, env, label, renderer)
        report.append(line)
        if not keep_going:
            break
    return "\n".join(report)


def main() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"daily_{datetime.now():%Y%m%d}.log"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    def emit(chunk: str) -> None:
        # progress lands on disk channel by channel, so a run killed by a
        # closed console still shows how far it got instead of vanishing
        with log.open("a", encoding="utf-8") as fh:
            fh.write(chunk.rstrip() + "\n\n")
        print(chunk, flush=True)

    emit(f"daily run {stamp}")
    for key in CHANNELS:
        for attempt in (1, 2):
            try:
                text = do_channel(key)
            except Exception:                           # noqa: BLE001
                text = f"{CHANNELS[key][0]}: crashed\n{traceback.format_exc()}"
            # a transient network or TTS failure is worth one more pass
            if attempt == 1 and re.search(r"failed|crashed", text):
                emit(f"{CHANNELS[key][0]}: attempt 1 failed, retrying")
                continue
            emit(text)
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
