# -*- coding: utf-8 -*-
"""Dezgo free text2image API (no login, no credits).

Captured from dezgo.com/app/text2image_sdxl:
  POST https://api.dezgo.com/text2image_sdxl   (multipart, x-dezgo-async: 1)
      -> {"id": "<token>"}
  GET  https://api.dezgo.com/async/<token>     (202 = queued, 200 = image/png)

Model list (free tier): juggernautxl_1024px, sdxl, ...
"""

import os
import time
import uuid

import urllib3

urllib3.disable_warnings()

API = "https://api.dezgo.com/text2image_sdxl"
ASYNC = "https://api.dezgo.com/async/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")

# session tokens from the browser (refresh them with refresh_tokens() if 403)
TOK = {
    "x-ctoken": os.environ.get("DEZGO_CTOKEN", "mzCZH4MnaMtV1tplxDQNfA=="),
    "x-htoken": os.environ.get("DEZGO_HTOKEN",
        "lgLkOASREOqsbntBVIhz/GXAkTjYuONk85s8U1hSTso2Tyl+0Ts1AQJLVyX5Bf09WLwctdpRT5ZPC5ZmwOsP8A=="),
    "x-ntoken": os.environ.get("DEZGO_NTOKEN", str(uuid.uuid4())),
    "x-wtoken": os.environ.get("DEZGO_WTOKEN", "4866692274162970785"),
}


def _headers():
    h = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US",
        "Origin": "https://dezgo.com",
        "Referer": "https://dezgo.com/",
        "content-type": "multipart/form-data",
        "x-dezgo-async": "1",
        "x-dezgo-web": "1",
        "x-d-method": "text2image_sdxl",
        "x-v": "5",
    }
    h.update(TOK)
    return h


def generate(prompt, out, width=1024, height=1024, steps=20, guidance=7.0,
             model="juggernautxl_1024px", negative="", seed=None, log=print):
    import requests

    fields = {
        "prompt": prompt,
        "model": model,
        "count": "1",
        "transparent_background": "False",
        "width": str(int(width)),
        "height": str(int(height)),
        "lora1_strength": "1",
        "lora2_strength": "1",
        "refiner": "False",
        "negative_prompt": negative or "",
        "guidance": str(guidance),
        "steps": str(int(steps)),
        "sampler": "auto",
        "seed": str(int(seed) if seed else int(time.time()) % 2000000000),
        "format": "png",
    }
    boundary = "----dezgo%s" % uuid.uuid4().hex
    body = []
    for k, v in fields.items():
        body.append("--%s\r\nContent-Disposition: form-data; name=%s\r\n\r\n%s\r\n"
                    % (boundary, k, v))
    body.append("--%s--" % boundary)
    body = "".join(body).encode("utf-8")

    h = _headers()
    h["content-type"] = "multipart/form-data; boundary=%s" % boundary

    log("[dezgo] POST %s %dx%d steps=%d" % (model, width, height, steps))
    r = requests.post(API, data=body, headers=h, timeout=120)
    if r.status_code not in (200, 202):
        raise RuntimeError("dezgo POST %s: %s" % (r.status_code, r.text[:300]))
    token = r.json().get("id")
    if not token:
        raise RuntimeError("dezgo no id: %s" % r.text[:300])

    gh = {"User-Agent": UA, "Origin": "https://dezgo.com", "Referer": "https://dezgo.com/"}
    t0 = time.time()
    while time.time() - t0 < 420:
        g = requests.get(ASYNC + token, headers=gh, timeout=90, stream=True)
        if g.status_code == 200:
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            with open(out, "wb") as f:
                for chunk in g.iter_content(65536):
                    f.write(chunk)
            log("[dezgo] saved %s (%.0fs, %s)" % (out, time.time() - t0,
                                                  os.path.getsize(out)))
            g.close()
            return out
        g.close()
        time.sleep(4)
    raise RuntimeError("dezgo timeout after %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    import sys
    generate(sys.argv[1], sys.argv[2],
             int(sys.argv[3]) if len(sys.argv) > 3 else 1024,
             int(sys.argv[4]) if len(sys.argv) > 4 else 1024)
