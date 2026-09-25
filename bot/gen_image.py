# -*- coding: utf-8 -*-
"""Multi-source image generator for the chess YouTube bot.

    generate_image(prompt, out, width, height)  ->  path or raises

Order (cheapest / most reliable first):
  1. pollinations   - no key, unlimited-ish, works from GitHub Actions
  2. pollinations   - official gen endpoint (needs POLLINATIONS_API_KEY)
  3. huggingface    - $0.10 monthly free credit (needs HF_TOKEN)
  4. cloudflare     - 10k neurons/day free (needs CF_ACCOUNT_ID + CF_API_TOKEN)
  5. runware        - $2 trial credit (needs RUNWARE_API_KEY)

Every source is optional: a source whose key/env var is missing is skipped,
so the bot always works even with only Pollinations configured.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}


def _get(url, headers=None, timeout=140):
    h = dict(UA)
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.read(), dict(resp.headers)


def _post_json(url, payload, headers=None, timeout=140):
    import json
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    h.update(UA)
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _save(data, out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    return out


# ---------------------------------------------------------------- 1. pollinations (anon)
def src_pollinations(prompt, out, width=1280, height=720, seed=None):
    seed = seed or int(time.time() * 1000) % 1000000
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
           "?width=%d&height=%d&nologo=true&model=flux&seed=%d" % (width, height, seed))
    data, hdr = _get(url, timeout=150)
    if len(data) < 8000 or not _looks_like_image(data):
        ct = hdr.get("content-type", "?")
        raise RuntimeError("pollinations: bad response %s %dB" % (ct, len(data)))
    return _save(data, out)


def _looks_like_image(b):
    return (b[:3] == b"\xff\xd8\xff" or b[:8] == b"\x89PNG\r\n\x1a\n"
            or b[:4] == b"RIFF" or b[:6] in (b"GIF87a", b"GIF89a"))


# ---------------------------------------------------------------- 2. pollinations (official)
def src_pollinations_keyed(prompt, out, width=1280, height=720, seed=None):
    key = os.environ.get("POLLINATIONS_API_KEY")
    if not key:
        raise RuntimeError("pollinations-keyed: POLLINATIONS_API_KEY missing")
    url = ("https://gen.pollinations.ai/image/" + urllib.parse.quote(prompt) +
           "?model=flux&width=%d&height=%d&nologo=true&seed=%d" %
           (width, height, seed or int(time.time() * 1000) % 1000000))
    data, _ = _get(url, headers={"Authorization": "Bearer " + key}, timeout=150)
    if len(data) < 8000:
        raise RuntimeError("pollinations-keyed: %dB" % len(data))
    return _save(data, out)


# ---------------------------------------------------------------- 3. huggingface inference
def src_huggingface(prompt, out, width=1280, height=720):
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("huggingface: HF_TOKEN missing")
    model = os.environ.get("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
    url = "https://router.huggingface.co/v1/images/generations"
    r = _post_json(url, {"model": model, "prompt": prompt, "n": 1,
                         "width": width, "height": height},
                   headers={"Authorization": "Bearer " + token}, timeout=150)
    import base64
    item = (r.get("data") or [{}])[0]
    if item.get("b64_json"):
        return _save(base64.b64decode(item["b64_json"]), out)
    if item.get("url"):
        data, _ = _get(item["url"])
        return _save(data, out)
    raise RuntimeError("huggingface: no image in response")


# ---------------------------------------------------------------- 4. cloudflare workers ai
def src_cloudflare(prompt, out, width=1280, height=720):
    acc, tok = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not acc or not tok:
        raise RuntimeError("cloudflare: CF_ACCOUNT_ID / CF_API_TOKEN missing")
    model = os.environ.get("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    url = "https://api.cloudflare.com/client/v4/accounts/%s/ai/run/%s" % (acc, model)
    r = _post_json(url, {"prompt": prompt, "width": width, "height": height,
                         "num_steps": 4, "num_images": 1},
                   headers={"Authorization": "Bearer " + tok}, timeout=150)
    import base64
    img = r.get("result", {}).get("images", [{}])[0]
    if img.get("b64_json"):
        return _save(base64.b64decode(img["b64_json"]), out)
    if img.get("url"):
        data, _ = _get(img["url"])
        return _save(data, out)
    raise RuntimeError("cloudflare: no image: %s" % str(r)[:200])


# ---------------------------------------------------------------- 5. runware
def src_runware(prompt, out, width=1280, height=720):
    key = os.environ.get("RUNWARE_API_KEY")
    if not key:
        raise RuntimeError("runware: RUNWARE_API_KEY missing")
    r = _post_json("https://api.runware.ai/v1/image/generation",
                   [{"type": "imageGeneration", "taskType": "image",
                     "model": os.environ.get("RUNWARE_MODEL", "flux-1-dev-fast"),
                     "prompt": prompt, "width": width, "height": height,
                     "steps": 20, "numberResults": 1}],
                   headers={"Authorization": "Bearer " + key}, timeout=150)
    import base64
    item = (r.get("data") or [{}])[0]
    if item.get("b64Image"):
        return _save(base64.b64decode(item["b64Image"]), out)
    if item.get("imageURL"):
        data, _ = _get(item["imageURL"])
        return _save(data, out)
    raise RuntimeError("runware: no image: %s" % str(r)[:200])


# ---------------------------------------------------------------- 0. huggingface space (no key)
_Z_SPACE = os.environ.get("ZIMAGE_SPACE", "mrfakename/Z-Image-Turbo")
_z_api = {}


def _z_build(param):
    """Value for one Gradio parameter of the Z-Image space (or None = skip)."""
    import re
    name = str(param.get("parameter_name") or param.get("label") or "").lower()
    typ = str(param.get("python_type", {}).get("type", ""))
    dflt = param.get("parameter_default")
    m = re.search(r"between\s+(-?[\d.]+)\s+and\s+(-?[\d.]+)",
                  str(param.get("type", {}).get("description", "")))
    mn, mx = (float(m.group(1)), float(m.group(2))) if m else (None, None)

    def clamp(v):
        if mn is not None and v < mn:
            v = mn
        if mx is not None and v > mx:
            v = mx
        return v

    if "image" in typ or str(param.get("component", "")).lower() == "image":
        return None
    if "str" in typ:
        if "negative" in name:
            return ""
        return dflt if dflt is not None else ""
    if "bool" in typ:
        return dflt if dflt is not None else False
    if "float" in typ or "int" in typ:
        if "seed" in name:
            v = clamp(int(time.time() * 1000) % 1000000)
        elif "width" in name:
            v = clamp(width_hint[0])
        elif "height" in name:
            v = clamp(width_hint[1])
        elif dflt is not None:
            v = clamp(dflt)
        elif "step" in name:
            v = clamp(4)
        elif mn is not None:
            v = mn
        else:
            v = 1
        return int(round(v)) if "int" in typ else float(v)
    return dflt


width_hint = (1280, 720)


def src_zimage(prompt, out, width=1280, height=720):
    """Free Hugging Face Space (Z-Image-Turbo), no account, no key."""
    try:
        from gradio_client import Client
    except ImportError:
        raise RuntimeError("zimage: gradio_client not installed (pip install gradio_client)")
    global width_hint
    width_hint = (width, height)
    if _z_api.get("space") != _Z_SPACE:
        c = Client(_Z_SPACE, verbose=False)
        info = c.view_api(return_format="dict", print_info=False)
        for name, ep in (info.get("named_endpoints") or {}).items():
            if not any("image" in str(r.get("label", "")).lower() or
                       "image" in json.dumps(r.get("type", {})).lower()
                       for r in (ep.get("returns") or [])):
                continue
            args = [_z_build(p) for p in (ep.get("parameters") or [])]
            if any(a is None for a in args):
                continue
            _z_api.update(space=_Z_SPACE, client=c, name=name, args=args)
            break
        if _z_api.get("space") != _Z_SPACE:
            raise RuntimeError("zimage: no usable endpoint in %s" % _Z_SPACE)
    args = list(_z_api["args"])
    if args:
        args[0] = prompt
    res = _z_api["client"].predict(*args, api_name=_z_api["name"])
    path = None
    for v in (res.values() if isinstance(res, dict) else
              (res if isinstance(res, (list, tuple)) else [res])):
        if isinstance(v, dict) and v.get("path"):
            path = v["path"]
            break
        if isinstance(v, str) and (v.startswith("http") or os.path.exists(v)):
            path = v
            break
    if not path:
        raise RuntimeError("zimage: no image in response: %r" % str(res)[:160])
    data = _get(path)[0] if str(path).startswith("http") else open(path, "rb").read()
    if not _looks_like_image(data):
        raise RuntimeError("zimage: not an image (%dB)" % len(data))
    return _save(data, out)


# ---------------------------------------------------------------- local CPU (no key, unlimited)
def src_local(prompt, out, width=1280, height=720):
    if os.environ.get("SD_DISABLE") == "1":
        raise RuntimeError("local-sd: disabled by SD_DISABLE=1")
    try:
        from local_sd import generate as _sd
    except ImportError:
        from bot.local_sd import generate as _sd
    return _sd(prompt, out, width, height)


SOURCES = [
    ("local-sd", src_local),
    ("zimage", src_zimage),
    ("pollinations", src_pollinations),
    ("pollinations-keyed", src_pollinations_keyed),
    ("huggingface", src_huggingface),
    ("cloudflare", src_cloudflare),
    ("runware", src_runware),
]


def generate_image(prompt, out, width=1280, height=720, tries=2, log=print):
    """Try every configured source until one returns a file. Returns (path, source)."""
    errors = []
    for name, fn in SOURCES:
        for attempt in range(tries):
            try:
                path = fn(prompt, out, width=width, height=height)
                log("[img] %s -> %s" % (name, path))
                return path, name
            except Exception as e:          # noqa: BLE001 - every source is best-effort
                errors.append("%s#%d: %s" % (name, attempt + 1, e))
                log("[img] %s failed: %s" % (name, e))
                time.sleep(3)
    raise RuntimeError("all image sources failed: " + " | ".join(errors))


if __name__ == "__main__":
    import sys
    prompt = sys.argv[1]
    out = sys.argv[2]
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 1280
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 720
    print(generate_image(prompt, out, w, h))
