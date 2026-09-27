# -*- coding: utf-8 -*-
"""Generate music (copyright-free, randomized per track), long video and shorts.
Video style: static board frames, hard cuts (no zoom, no fade), 15s per puzzle."""
import os, math, wave, struct, json, random, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from board_renderer import render_board, render_frame_wide
from PIL import Image as I

def get_ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

# ---------------- music (randomized; every track is different) --------------------
PROGRESSIONS = [
    [[57,60,64,69],[53,57,60,65],[48,52,55,60],[55,59,62,67]],
    [[62,65,69,72],[57,60,64,67],[53,57,60,65],[55,59,62,66]],
    [[52,55,59,62],[57,60,64,67],[50,53,57,60],[48,52,55,59]],
    [[60,64,67,71],[65,69,72,76],[62,65,69,72],[67,71,74,77]],
    [[45,52,57,60],[41,48,53,57],[43,50,55,59],[48,55,60,64]],
    [[58,62,65,70],[51,55,58,63],[56,60,63,68],[53,57,60,65]],
]

def make_music(path, seconds=75, sr=44100, rng=None, style="calm", gain=0.9):
    """One continuous piece for the WHOLE video.
    style="calm"  : slow piano + violin pad (10-min long videos)
    style="trend" : brighter, faster, beat-driven loop for Shorts - same chord
                    vocabulary (still 100% original / copyright-free), but with
                    a kick, off-beat hats and a sub bass so it feels catchy.
    gain: peak level after normalisation (shorts sit quieter on purpose).
    Each video gets its own random key/progression/tempo."""
    import random
    rng = rng or random.Random()
    key_shift = rng.choice([-5,-3,-2,0,2,3,5,7])
    chords = [[n + key_shift for n in ch] for ch in rng.choice(PROGRESSIONS)]
    if style == "trend":
        beat = rng.choice([0.30, 0.34, 0.38])     # upbeat Shorts tempo
    else:
        beat = rng.choice([0.55, 0.62, 0.7])      # calm tempo
    steps_per_chord = 8
    total = int(seconds * sr)
    samples = [0.0] * total
    vib_hz, vib_amt = rng.uniform(4.5, 5.5), 0.004  # violin vibrato

    def f(n): return 440.0 * 2**((n - 69) / 12.0)

    # --- violin pad: slow attack, sustained, vibrato (one note per chord, top voice)
    t0, ci = 0, 0
    while t0 < total:
        chord = chords[ci % len(chords)]
        seg_len = int(steps_per_chord*beat*sr)
        for k, note in enumerate(chord):
            fr = f(note - 12)
            for j in range(min(seg_len, total - t0)):
                t = j / sr
                env = min(1, t/1.2) * min(1, (seg_len/sr - t)/1.5)
                vib = 1 + vib_amt*math.sin(2*math.pi*vib_hz*t)
                samples[t0 + j] += 0.045 * env * (
                    math.sin(2*math.pi*fr*vib*t) + 0.3*math.sin(2*math.pi*2.001*fr*t))
        t0 += seg_len; ci += 1

    # --- piano: gentle melody notes (decaying harmonics), one per beat
    t0, ci = 0, 0
    while t0 < total:
        chord = chords[ci % len(chords)]
        seg_len = int(steps_per_chord*beat*sr)
        pattern = [rng.choice(chord) + 12 for _ in range(steps_per_chord)]
        for s, note in enumerate(pattern):
            fr = f(note)
            start = t0 + int(s*beat*sr)
            dur = int(rng.uniform(1.2, 2.0)*sr)
            for j in range(min(dur, total - start)):
                t = j / sr
                env = math.exp(-1.8*t)
                v = 0.11 * env * (
                    math.sin(2*math.pi*fr*t)
                    + 0.5*math.sin(2*math.pi*2*fr*t)*math.exp(-2*t)
                    + 0.25*math.sin(2*math.pi*3*fr*t)*math.exp(-4*t))
                if start + j < total: samples[start + j] += v
        t0 += seg_len; ci += 1

    # --- Shorts only: beat layer (kick + off-beat hats + sub bass) ---------
    if style == "trend":
        step = beat * sr
        t0 = 0
        while t0 < total:                          # kick on every beat
            for j in range(int(0.14 * sr)):
                if t0 + j >= total: break
                tt = j / sr
                fr = 78 * math.exp(-22 * tt) + 42  # pitch drop = punchy kick
                samples[t0 + j] += 0.55 * math.exp(-16 * tt) * math.sin(
                    2 * math.pi * fr * tt)
            hs = t0 + int(step / 2)                # crisp hat on the off-beat
            for j in range(int(0.05 * sr)):
                if hs + j >= total: break
                samples[hs + j] += 0.16 * math.exp(-70 * j / sr) * rng.uniform(-1, 1)
            t0 += int(step)
        t0, ci = 0, 0                              # sub bass on the chord root
        while t0 < total:
            root = f(chords[ci % len(chords)][0] - 24)
            dur = int(step * 2)
            for j in range(min(dur, total - t0)):
                tt = j / sr
                env = min(1, tt / 0.02) * math.exp(-2.2 * tt)
                samples[t0 + j] += 0.34 * env * math.sin(2 * math.pi * root * tt)
            t0 += dur; ci += 1

    # peak-normalise -> predictable level, never clips
    peak = max(1e-9, max(abs(s) for s in samples))
    k = gain / peak
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(
            struct.pack("<h", int(max(-1, min(1, s * k)) * 32000)) for s in samples))

# ---------------- frames ---------------------------------------------------------
def to_bg(path, w, h):
    img = I.open(path)
    scale = min(w/img.width, h/img.height)*0.95
    img = img.resize((int(img.width*scale), int(img.height*scale)), I.LANCZOS)
    bg = I.new("RGB", (w, h), (36, 37, 38))
    bg.paste(img, ((w-img.width)//2, (h-img.height)//2))
    return bg

def turn_text(fen):
    return "White to play" if fen.split()[1] == "w" else "Black to play"

def board_frame(pz, i, out_dir, tag, w, h, suffix="q"):
    """16:9 (long video) -> the board sits a bit to the LEFT covering that whole
    side, every line of text on its RIGHT, all of it in gold.
    9:16 (short)      -> the stacked layout that already works vertically.
    The solution is never drawn, so the answer is not shown."""
    q = os.path.join(out_dir, f"{tag}_{suffix}{i}.png")
    title = f"Puzzle #{i}  •  Rating {pz['rating']}"
    top2 = f"{turn_text(pz['fen'])} — Find the best move!"
    foot = "Answer in the comments"
    foot2 = "Subscribe & Follow — don't forget!"
    wide = (w, h) == (1920, 1080)
    if wide:
        render_frame_wide(pz["fen"], w, h, title=title, top2=top2, foot=foot,
                          foot2=foot2, reveal=False).save(q)
    else:
        render_board(pz["fen"], title=title, top2=top2, foot=foot,
                     foot2=foot2, gold=True).save(q)
    frame = os.path.join(out_dir, f"{tag}_{suffix}{i}_f.png")
    if wide:
        I.open(q).convert("RGB").save(frame)
        os.remove(q)
    else:
        to_bg(q, w, h).save(frame)
        os.remove(q)
    return frame

# ---------------- videos ----------------------------------------------------------
def make_video(puzzles, out_dir, tag, seg=15, ff=None):
    """5 puzzles -> long video (16:9). Static frames, hard cuts, one continuous music piece."""
    os.makedirs(out_dir, exist_ok=True)
    W, H = 1920, 1080
    # one continuous piece of music for the whole video
    total = seg * len(puzzles)
    music = os.path.join(out_dir, f"{tag}_music.wav")
    make_music(music, seconds=total, rng=random.Random(tag),
               style="calm", gain=0.85)   # long video: calm + not loud
    parts = []
    for i, pz in enumerate(puzzles, 1):
        frame = board_frame(pz, i, out_dir, tag, W, H)
        out = os.path.join(out_dir, f"{tag}_seg{i}.mp4")
        subprocess.run([ff, "-y", "-loop","1","-t",str(seg),"-i",frame,
            "-f","lavfi","-t",str(seg),"-i","anullsrc=r=44100:cl=stereo",
            "-filter_complex", f"[0:v]scale={W}:{H},fps=25[v]",
            "-map","[v]","-map","1:a","-t",str(seg),"-c:v","libx264","-preset","veryfast",
            "-pix_fmt","yuv420p","-c:a","aac","-shortest", out],
            check=True, capture_output=True)
        os.remove(frame)
        parts.append(out)
    lst = os.path.join(out_dir, f"{tag}_list.txt")
    with open(lst, "w") as f:
        for p in parts: f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")
    final = os.path.join(out_dir, f"{tag}_video.mp4")
    subprocess.run([ff, "-y", "-f","concat","-safe","0","-i",lst,"-i",music,
        "-map","0:v","-map","1:a",
        "-af","afade=t=out:st={:.1f}:d=2".format(total-2),
        "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
        "-c:a","aac","-shortest", final],
        check=True, capture_output=True)
    for p in parts: os.remove(p)
    os.remove(lst); os.remove(music)
    return final

def make_short(pz, out_dir, tag, i, ff=None, seg=15):
    """One puzzle -> vertical Short (9:16), static frame, its own random music."""
    os.makedirs(out_dir, exist_ok=True)
    sw, sh = 1080, 1920
    frame = board_frame(pz, i, out_dir, tag, sw, sh, suffix="s")
    music = os.path.join(out_dir, f"{tag}_sm{i}.wav")
    make_music(music, seconds=seg, rng=random.Random(f"{tag}short{i}"),
               style="trend", gain=0.55)  # catchy beat, but deliberately quiet
    final = os.path.join(out_dir, f"{tag}_short{i}.mp4")
    subprocess.run([ff, "-y", "-loop","1","-t",str(seg),"-i",frame,"-i",music,
        "-filter_complex", f"[0:v]scale={sw}:{sh},fps=25[v]",
        "-map","[v]","-map","1:a","-t",str(seg),"-c:v","libx264","-preset","veryfast",
        "-pix_fmt","yuv420p","-c:a","aac","-shortest", final],
        check=True, capture_output=True)
    os.remove(frame); os.remove(music)
    return final

if __name__ == "__main__":
    ff = get_ffmpeg()
    demo = json.loads(open(os.path.join(HERE, "..", "puzzles_pool.jsonl"),
                           encoding="utf-8").readline())
    demo = [demo] * 5
    v = make_video(demo, os.path.join(HERE, "out"), "test", ff=ff)
    s = make_short(demo[0], os.path.join(HERE, "out"), "test", 1, ff=ff)
    print("OK:", v, "|", s)
