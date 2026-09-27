# -*- coding: utf-8 -*-
"""Science channel thumbnail (16:9 long / 9:16 short).

  photo  : Pexels science photo (free, unlimited, cached in photo_lib.json)
  text   : rotating hook from hooks_lib.SCIENCE_HOOKS (11k+ lines)
  frame  : fire-like glow, a different colour for every video / short
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gold_thumb import gold_gradient, load_font, wrap            # noqa: E402
from glow_frame import add_glow, accent_gradient, next_color     # noqa: E402
from hooks_lib import SCIENCE_HOOKS                              # noqa: E402
import photo_lib                                                 # noqa: E402

MODES = {"long": (1280, 720), "short": (720, 1280)}
IDX = os.path.join(HERE, "..", "state", "science_thumb.json")


def _next_hook():
    os.makedirs(os.path.dirname(IDX), exist_ok=True)
    i = -1
    if os.path.exists(IDX):
        try:
            i = int(json.load(open(IDX, encoding="utf-8")).get("h", -1))
        except Exception:                              # noqa: BLE001
            i = -1
    i = (i + 1) % len(SCIENCE_HOOKS)
    json.dump({"h": i}, open(IDX, "w", encoding="utf-8"))
    return SCIENCE_HOOKS[i]


def fit_cover(img, w, h):
    iw, ih = img.size
    s = max(w / iw, h / ih)
    nw, nh = int(iw * s + .5), int(ih * s + .5)
    img = img.resize((nw, nh), Image.LANCZOS)
    return img.crop(((nw - w) // 2, (nh - h) // 2, (nw - w) // 2 + w, (nh - h) // 2 + h))


def _text_block(base, text, accent, mode, max_h=None):
    """The headline sits in the reserved strip ABOVE the photo, so it never
    covers the picture. `max_h` = how tall that strip is."""
    W, H = base.size
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    maxw = W - (70 if mode == "long" else 44)
    limit = max_h if max_h else int(H * 0.46)
    size = int(W * 0.075 if mode == "long" else W * 0.115)
    while size >= 30:
        f = load_font(size)
        lines = wrap(probe, text, f, maxw)
        if len(lines) * int(size * 1.12) <= limit:
            break
        size -= 4
    font = load_font(size)
    lines = wrap(probe, text, font, maxw)
    lh, gap, padx, pady = int(size * 1.12), 9, 20, 10

    boxes, yy, y0 = [], H * 0.035, H * 0.035
    for ln in lines:
        tw = probe.textlength(ln, font=font)
        bw, bh = int(tw) + padx * 2, lh + pady * 2
        boxes.append((ln, tw, bw, bh))
        yy += bh + gap
    total = yy - y0 - gap

    sh = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sh)
    yy = y0
    for _, _, bw, bh in boxes:
        sd.rounded_rectangle([(W - bw) // 2 + 6, yy + 7, (W - bw) // 2 + bw + 6, yy + bh + 7],
                             radius=9, fill=255)
        yy += bh + gap
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    base.paste((0, 0, 0), (0, 0), sh)

    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    d = ImageDraw.Draw(base)
    yy = y0
    for ln, tw, bw, bh in boxes:
        bx = (W - bw) // 2
        d.rounded_rectangle([bx, yy, bx + bw, yy + bh], radius=9, fill=(0, 0, 0))
        md.text((bx + padx, yy + pady - int(lh * 0.14)), ln, font=font, fill=255)
        yy += bh + gap

    base.paste(accent_gradient(W, H, accent), (0, 0), mask)
    return base, int(total)


TOPIC_FORMS = [
    "THE SCIENCE OF %s",
    "WHY %s TAKES OVER YOUR BRAIN",
    "WHAT %s DOES TO YOUR BODY",
    "WHAT NOBODY TELLS YOU ABOUT %s",
    "%s EXPLAINED BY SCIENCE",
    "WHY %s CONTROLS YOUR DECISIONS",
    "THE TRUTH ABOUT %s",
    "HOW %s CHANGES YOUR BODY",
    "THIS IS WHY %s HAPPENS",
    "WHAT HAPPENS INSIDE YOUR BRAIN DURING %s",
    "THE UNTOLD SCIENCE OF %s",
    "YOU NEED TO KNOW THIS ABOUT %s",
]


# topic -> how to find the matching photo (queries / must-have / must-not-have)
TOPIC_PRESETS = {
    "anger": {
        "queries": ["angry face close up", "rage scream", "screaming",
                    "angry man shouting", "yelling", "expressing intense anger"],
        "required": ["yell", "scream", "shout", "open mouth", "anger", "angry"],
        "forbidden": ["megaphone", "wire"],
    },
    "sleep": {
        "queries": ["sleeping bed", "tired yawning", "insomnia"],
        "required": ["sleep", "tired", "yawn", "bed", "rest"],
        "forbidden": [],
    },
    "stress": {
        "queries": ["stressed person", "headache stress", "overwhelmed"],
        "required": ["stress", "tired", "headache", "overwhelm", "tension"],
        "forbidden": [],
    },
    "memory": {
        "queries": ["brain concept", "studying notes", "focused thinking"],
        "required": ["brain", "study", "focus", "think", "memory", "read"],
        "forbidden": [],
    },
}


def preset_for(topic):
    t = topic.lower()
    for key, val in TOPIC_PRESETS.items():
        if key in t or t in key:
            return val
    return {}


def topic_hook(topic):
    """Rotating, topic-specific English hook (state/topic_hook.json)."""
    t = " ".join(topic.upper().split())
    pool = [f % t for f in TOPIC_FORMS]
    path = os.path.join(HERE, "..", "state", "topic_hook.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    i = -1
    if os.path.exists(path):
        try:
            i = int(json.load(open(path, encoding="utf-8")).get("h", -1))
        except Exception:                              # noqa: BLE001
            i = -1
    i = (i + 1) % len(pool)
    json.dump({"h": i}, open(path, "w", encoding="utf-8"))
    return pool[i]


def make(out, mode="long", hook=None, category="science", accent=None, photo=None,
         topic=None):
    """topic -> the photo AND the text both follow the video's subject."""
    hook = hook or None
    W, H = MODES[mode]
    if topic:
        pre = preset_for(topic)
        ent, path = photo_lib.get_photo_query(
            topic, os.path.join(HERE, "..", "state", "_tmp_sci.jpg"), **pre)
        photo = path
        if hook is None:
            hook = topic_hook(topic)
    elif photo is None:
        photo = photo_lib.get_photo(category, os.path.join(HERE, "..", "state", "_tmp_sci.jpg"))
    img = Image.open(photo).convert("RGB")
    from thumb_layout import build_canvas
    zone = (0.28, 0.96) if mode == "long" else (0.36, 0.97)
    base = build_canvas(img, W, H, zone=zone)

    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.3, -H * 0.4, W * 1.3, H * 1.4], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(min(W, H) * 0.14))
    base = Image.composite(base, Image.new("RGB", (W, H), (6, 7, 9)), vig)

    text = (hook or _next_hook()).upper()
    if accent is None:
        try:
            import pin_lib                                  # noqa: PLC0415
            accent = pin_lib.accent_of(img)                 # harmonises w/ photo
        except Exception:                                   # noqa: BLE001
            accent = next_color()[1]
    base, _ = _text_block(base, text, accent, mode,
                          max_h=int(H * zone[0]) - 14)
    base = add_glow(base, accent, strength=1.0, seed=abs(hash(text)) & 0xFFFF)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    base.save(out, quality=95)
    return out, text, accent


if __name__ == "__main__":
    args = sys.argv[1:]
    out = args[0] if args else r"C:\Users\USER\Desktop\chess_sample\sci_thumb.jpg"
    mode = args[1] if len(args) > 1 else "long"
    hook = topic = None
    for a in args[2:]:
        if a.startswith("--topic="):
            topic = a[len("--topic="):]
        elif a.startswith("--hook="):
            hook = a[len("--hook="):]
    p, t, c = make(out, mode, hook, topic=topic)
    print("saved", p, "|", t, "| rgb", c)
