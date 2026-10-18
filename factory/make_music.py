# -*- coding: utf-8 -*-
"""Generate the mellow background bed mixed under narration.

Pure stdlib (wave/math/struct) so it runs identically on the GitHub
runner: an 8-chord warm pad loop, seamless at the loop point, peak
normalised. factory.py mixes it at volume=0.10 (-20 dB) so the voice
stays fully forward and the music is a texture, never a competitor.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

SR = 44100
CHORD_SECONDS = 4.0
FADE = 0.5          # raised-cosine attack / release per chord
TREMOLO_HZ = 0.22   # slow breathing on the whole bed

# Cmaj7  Am7  Fmaj7  G6  Cmaj7  Am7  Dm7  G7sus4 — warm, unhurried
_CHORDS = [
    ("C3", "E3", "G3", "B3", "E4"),
    ("A2", "C3", "E3", "G3", "C4"),
    ("F2", "A2", "C3", "E3", "A3"),
    ("G2", "B2", "D3", "E3", "B3"),
    ("C3", "E3", "G3", "B3", "G4"),
    ("A2", "C3", "E3", "G3", "E4"),
    ("D3", "F3", "A3", "C4", "F4"),
    ("G2", "B2", "D3", "F3", "A3"),
]

_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _freq(name: str) -> float:
    letter, octave = name[0], int(name[-1])
    midi = 12 * (octave + 1) + _SEMI[letter]
    return 440.0 * 2 ** ((midi - 69) / 12)


def _raised(t: float) -> float:
    """Raised-cosine ramp for t in [0, 1]."""
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ensure_bed(path: Path) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)

    total = int(len(_CHORDS) * CHORD_SECONDS * SR)
    fade_n = int(FADE * SR)
    # two slightly detuned layers per note = chorus warmth
    detune = 2 ** (4 / 1200)

    left = [0.0] * (total + fade_n)
    right = [0.0] * (total + fade_n)

    for ci, chord in enumerate(_CHORDS):
        start = int(ci * CHORD_SECONDS * SR)
        notes = [_freq(n) for n in chord]
        for vi, base in enumerate(notes):
            amps = (1.0, 0.30, 0.10)          # fundamental + soft partials
            for det, buf in ((1.0, left), (detune * (1.0008 ** vi), right)):
                f = base * det
                w = 2 * math.pi * f / SR
                for n in range(0, int((CHORD_SECONDS + FADE) * SR), 64):
                    idx = start + n
                    if idx >= len(buf):
                        break
                    t = n / SR
                    if t < FADE:
                        env = _raised(t / FADE)
                    elif t > CHORD_SECONDS:
                        env = _raised(1.0 - (t - CHORD_SECONDS) / FADE)
                    else:
                        env = 1.0
                    if env <= 0.0:
                        continue
                    # sum partials over the 64-sample block (block-constant
                    # phase is inaudible at these frequencies and 10x faster)
                    s = 0.0
                    for k, a in enumerate(amps, start=1):
                        s += a * math.sin(w * k * (n + 32))
                    buf[idx] += s * env * (0.085 / len(notes))

    # wrap the tail into the head: the last chord's release blends into the
    # first chord's attack so -stream_loop never clicks
    overflow = len(left) - total
    for i in range(overflow):
        left[i] += left[total + i]
        right[i] += right[total + i]
    left = left[:total]
    right = right[:total]

    peak = max(max(abs(v) for v in left), max(abs(v) for v in right)) or 1.0
    gain = 0.85 / peak

    frames = bytearray()
    for i in range(total):
        trem = 1.0 + 0.10 * math.sin(2 * math.pi * TREMOLO_HZ * i / SR)
        l = int(max(-1.0, min(1.0, left[i] * gain * trem)) * 32767)
        r = int(max(-1.0, min(1.0, right[i] * gain * trem)) * 32767)
        frames += struct.pack("<hh", l, r)

    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    return path


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "assets" / "mellow_bed.wav"
    ensure_bed(out)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
