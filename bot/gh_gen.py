# -*- coding: utf-8 -*-
"""Generate an image on GitHub Actions (public repo Fyosamu/sd-gen) and pull it
back as a file.  Costs nothing - no credits, unlimited minutes on a public repo.

    generate(prompt, out, width=1280, height=720)  ->  path

Env:
    GH_TOKEN   GitHub token with repo scope
    GH_REPO    default "Fyosamu/sd-gen"
    GH_MODEL   default "stabilityai/sd-xl-base-1.0"-style diffusers id

First run downloads the model (~3.5 GB, cached afterwards); a render takes
roughly 15-30 minutes on the 4 vCPU / 16 GB public runner.
"""

try:
    import netfix  # noqa: F401  DNS self-heal (dead private IP answers)
except ImportError:  # when imported as bot.gh_gen, bot/ is not on sys.path
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import netfix  # noqa: F401

import os
import time
import zipfile

API = "https://api.github.com"
REPO = os.environ.get("GH_REPO", "Fyosamu/sd-gen")
TOKEN = os.environ.get("GH_TOKEN", "")
WF = "image-gen.yml"
MODEL = os.environ.get("GH_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
NEGATIVE = os.environ.get(
    "GH_NEGATIVE",
    "blurry, low quality, deformed, extra fingers, bad anatomy, watermark, "
    "text, logo, cropped, worst quality")


def _h():
    return {
        "Authorization": "token %s" % TOKEN,
        "User-Agent": "thumb-bot",
        "Accept": "application/vnd.github+json",
    }


def _req(method, path, json_body=None, tries=6):
    import json as _json
    import http.client
    import urllib.error
    import urllib.request

    data = _json.dumps(json_body).encode() if json_body is not None else None
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(API + path, data=data, headers=_h(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            return _json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            body = e.read()[:200]
            if e.code in (403, 429) and attempt < tries - 1:      # rate limited
                time.sleep(15 * (attempt + 1))
                last = e
                continue
            raise RuntimeError("gh %s %s -> %s %s" % (method, path, e.code, body))
        except (urllib.error.URLError, http.client.RemoteDisconnected,
                ConnectionError, TimeoutError, OSError) as e:
            last = e
            if attempt < tries - 1:
                time.sleep(min(40, 3 * (2 ** attempt)))            # 3,6,12,24,40
    raise RuntimeError("gh %s %s failed after %s tries: %s" % (method, path, tries, last))


def trigger(prompt, width=1280, height=720, model=None):
    _req("POST", "/repos/%s/actions/workflows/%s/dispatches" % (REPO, WF), {
        "ref": "main",
        "inputs": {
            "prompt": prompt,
            "width": str(int(width)),
            "height": str(int(height)),
            "model": model or MODEL,
        },
    })


def _wait_idle(max_wait=1800, log=print):
    """Serialize dispatches: never start a run while another one is queued, so
    two local jobs cannot pick up each other's run/artifact."""
    t_end = time.time() + max_wait
    while time.time() < t_end:
        runs = _req("GET", "/repos/%s/actions/runs?per_page=30" % REPO)
        busy = [r for r in runs.get("workflow_runs", [])
                if r.get("event") == "workflow_dispatch"
                and r.get("status") in ("queued", "in_progress", "waiting", "requested")]
        if not busy:
            return
        log("[gh] %d other run(s) busy, waiting..." % len(busy))
        time.sleep(20)
    log("[gh] still busy after %ss - dispatching anyway" % max_wait)


def wait_run(since, timeout=7200, log=print):
    """Poll until MY run (the oldest dispatch created after `since`) finishes."""
    import calendar

    def _c(r):
        return calendar.timegm(time.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%SZ"))

    mine = None
    t_end = time.time() + timeout
    while time.time() < t_end:
        runs = _req("GET", "/repos/%s/actions/runs?per_page=30" % REPO)
        cands = sorted([r for r in runs.get("workflow_runs", [])
                        if r.get("created_at") and _c(r) + 5 >= since],
                       key=_c)                       # oldest first
        if cands and mine is None:
            mine = cands[0]["id"]
        run = next((r for r in cands if r["id"] == mine), None)
        if run is None and mine is not None:
            run = _req("GET", "/repos/%s/actions/runs/%s" % (REPO, mine))
        if run and run.get("conclusion"):
            return run
        if run:
            log("[gh] run %s %s..." % (mine, run.get("status")))
        time.sleep(20 if mine is None else 30)
    raise RuntimeError("gh run did not finish in %ss" % timeout)


def _download(url, timeout=180):
    """GET that drops the Authorization header on cross-host redirects
    (the artifact URL hands off to Azure blob storage, which rejects it)."""
    import urllib.parse

    class _StripAuth(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            r = super().redirect_request(req, fp, code, msg, headers, newurl)
            if r is not None:
                same = (urllib.parse.urlparse(newurl).netloc ==
                        urllib.parse.urlparse(req.full_url).netloc)
                if not same:
                    for store in (r.headers, r.unredirected_hdrs):
                        for k in list(store):
                            if k.lower() == "authorization":
                                del store[k]
            return r

    opener = urllib.request.build_opener(_StripAuth)
    req = urllib.request.Request(url, headers=_h())
    return opener.open(req, timeout=timeout)


def download(run_id, out, log=print):
    # run-scoped: repo-wide lists would hand back an older run's artifact
    art = _req("GET", "/repos/%s/actions/runs/%s/artifacts" % (REPO, run_id))
    items = [a for a in art.get("artifacts", [])
             if a.get("expired") is False and a.get("size_in_bytes", 0) > 1000]
    if not items:
        raise RuntimeError("no artifact for run %s" % run_id)
    aid = items[0]["id"]
    url = "%s/repos/%s/actions/artifacts/%s/zip" % (API, REPO, aid)
    blob, last = None, None
    for attempt in range(4):
        try:
            with _download(url) as r:
                blob = r.read()
            break
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    if blob is None:
        raise RuntimeError("artifact download failed: %s" % last)
    tmp = out + ".zip"
    with open(tmp, "wb") as f:
        f.write(blob)
    with zipfile.ZipFile(tmp) as z:
        names = [n for n in z.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
        if not names:
            raise RuntimeError("zip has no image: %s" % z.namelist())
        data = z.read(names[0])
    os.remove(tmp)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    log("[gh] saved %s (%s bytes)" % (out, len(data)))
    return out


def generate(prompt, out, width=1280, height=720, steps=None, log=print):
    if not TOKEN:
        raise RuntimeError("GH_TOKEN is not set")
    prompt = "%s, ultra detailed, sharp focus, photorealistic" % prompt
    log("[gh] dispatch SDXL: %.60s..." % prompt)
    _wait_idle(log=log)               # one run at a time -> no crossed wires
    t0 = time.time()
    trigger(prompt, width, height)
    run = wait_run(t0, log=log)
    if run.get("conclusion") != "success":
        raise RuntimeError("gh run %s ended with %s" % (run["id"], run.get("conclusion")))
    return download(run["id"], out, log=log)


if __name__ == "__main__":
    import sys
    generate(sys.argv[1], sys.argv[2],
             int(sys.argv[3]) if len(sys.argv) > 3 else 1280,
             int(sys.argv[4]) if len(sys.argv) > 4 else 720)
