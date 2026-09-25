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


def _req(method, path, json_body=None):
    import json as _json
    import urllib.error
    import urllib.request

    data = _json.dumps(json_body).encode() if json_body is not None else None
    req = urllib.request.Request(API + path, data=data, headers=_h(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError("gh %s %s -> %s %s" % (method, path, e.code, e.read()[:200]))
    return _json.loads(raw) if raw else None


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


def wait_run(since, timeout=3600, log=print):
    """Poll until the run created after `since` (epoch seconds) finishes."""
    import calendar

    started = None
    t_end = time.time() + timeout
    while time.time() < t_end:
        runs = _req("GET", "/repos/%s/actions/runs?per_page=5" % REPO)
        for r in runs.get("workflow_runs", []):
            if not r.get("created_at"):
                continue
            created = calendar.timegm(time.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%SZ"))
            if created + 5 < since:
                continue
            if r["status"] in ("queued", "in_progress", "waiting", "requested"):
                started = r
                break
            if started and r["id"] == started["id"] and r.get("conclusion"):
                return r
            if not started and r.get("conclusion") and created >= since:
                return r
        if started:
            log("[gh] run %s %s..." % (started["id"], started["status"]))
        time.sleep(30)
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
    art = _req("GET", "/repos/%s/actions/artifacts?per_page=5" % REPO)
    items = [a for a in art.get("artifacts", [])
             if a.get("expired") is False and a.get("size_in_bytes", 0) > 1000]
    if not items:
        raise RuntimeError("no artifact for run %s" % run_id)
    aid = items[0]["id"]
    with _download("%s/repos/%s/actions/artifacts/%s/zip" % (API, REPO, aid)) as r:
        blob = r.read()
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
