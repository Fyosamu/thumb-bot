# -*- coding: utf-8 -*-
"""Push the fresh beethoven pair through a flaky connection.

The morning's network drops killed the first attempt mid-chunk; this
retries upload.py itself (each run starts a clean resumable session)
and only stops when the ledger shows the pair - then it leaves the
owner the desktop note plus tray balloon with the links.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKEN = HERE.parent / "yt_auth" / "bio_token.json"
LEDGER = HERE / "state" / "uploaded_bio.json"
ATTEMPTS = 4


def notify(title: str, body: str, note: str) -> None:
    desktop = Path.home() / "Desktop"
    (desktop / "\u062e\u0628\u0631 \u0622\u067e\u0644\u0648\u062f.txt").write_text(
        note, encoding="utf-8")
    ps = ("Add-Type -AssemblyName System.Windows.Forms;"
          "Add-Type -AssemblyName System.Drawing;"
          "$n=New-Object System.Windows.Forms.NotifyIcon;"
          "$n.Icon=[System.Drawing.SystemIcons]::Information;"
          "$n.Visible=$true;"
          f"$n.ShowBalloonTip(30000,'{title}','{body}','Info');"
          "Start-Sleep 31;$n.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps])


def beethoven_entries() -> list:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    return [v for v in data["uploaded"].values()
            if str(v.get("file", "")).startswith("beethoven")]


def main() -> int:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["YT3_TOKEN_JSON"] = TOKEN.read_text(encoding="utf-8")

    for attempt in range(1, ATTEMPTS + 1):
        print(f"--- upload attempt {attempt}/{ATTEMPTS}", flush=True)
        res = subprocess.run(
            [sys.executable, str(HERE / "upload.py"),
             "--channel", "3", "--only", "beethoven beethoven_short"],
            cwd=HERE, env=env)
        if res.returncode == 0 and len(beethoven_entries()) >= 2:
            links = "\n".join(f"https://youtu.be/{v['videoId']}"
                              for v in beethoven_entries())
            note = ("beethoven pair is live on the biography channel\n"
                    f"{links}\n"
                    "the short publishes itself ~6 hours from now\n"
                    "curie tomorrow 10:00, davinci the day after")
            notify("YouTube factory",
                   "Beethoven pair LIVE - links on a desktop note", note)
            print(note, flush=True)
            return 0
        print(f"    attempt {attempt} did not land - waiting 25s",
              flush=True)
        time.sleep(25)

    notify("YouTube factory",
           "Upload still failing - network looks down",
           "4 upload attempts failed - the connection is unstable.\n"
           "Nothing is lost: samples are in the folder, the old pair is "
           "off the channel, and the fresh pair is one command away.")
    print("gave up after all attempts", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
