# -*- coding: utf-8 -*-
"""The owner said go: wait for the six renders, then go live.

    python _go_beethoven.py

1. waits until all six fresh renders exist and stop growing
2. runs _confirm_beethoven.py (samples -> desktop folder, old no-sub
   pair off the channel + out of the ledger, fresh pair uploaded)
3. leaves the owner a desktop note plus a tray balloon with the links
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out_bio"
SLUGS = ("beethoven", "beethoven_short", "curie", "curie_short",
         "davinci", "davinci_short")
DEADLINE = time.time() + 105 * 60


def wait_for_renders() -> list:
    """All six mp4s present and not growing -> the batch is done."""
    seen = {}
    while time.time() < DEADLINE:
        missing = [s for s in SLUGS if not (OUT / f"{s}.mp4").exists()]
        if missing:
            print(f"waiting on: {missing}", flush=True)
            time.sleep(20)
            continue
        growing = False
        for s in SLUGS:
            size = (OUT / f"{s}.mp4").stat().st_size
            if seen.get(s) != size:
                seen[s] = size
                growing = True
        if not growing:
            return []
        time.sleep(20)
    return [s for s in SLUGS
            if not (OUT / f"{s}.mp4").exists()
            or (OUT / f"{s}.mp4").stat().st_size != seen.get(s)]


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


def main() -> int:
    late = wait_for_renders()
    if late:
        note = ("beethoven upload did NOT run - renders unfinished: "
                + ", ".join(late))
        notify("YouTube factory", "Render still unfinished - check it", note)
        return 1
    print("all six renders are stable - going live", flush=True)
    res = subprocess.run(
        [sys.executable, str(HERE / "_confirm_beethoven.py")], cwd=HERE)
    if res.returncode != 0:
        note = "confirm script failed - see its output; nothing was lost"
        notify("YouTube factory", "Upload did not start - check it", note)
        return res.returncode
    led = json.loads((HERE / "state" / "uploaded_bio.json")
                     .read_text(encoding="utf-8"))
    pairs = [v for v in led["uploaded"].values()
             if str(v.get("file", "")).startswith("beethoven")]
    links = "\n".join(f"https://youtu.be/{v['videoId']}" for v in pairs)
    note = ("beethoven pair is live on the biography channel\n"
            f"{links}\n"
            "the short publishes itself ~6 hours from now\n"
            "curie tomorrow 10:00, davinci the day after")
    notify("YouTube factory", "Beethoven pair LIVE - links on a desktop note",
           note)
    print(note, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
