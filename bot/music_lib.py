# -*- coding: utf-8 -*-
"""Generate music (copyright-free, randomized per track), long video and shorts.
Video style: static board frames, hard cuts (no zoom, no fade), 15s per puzzle."""
import os, math, wave, struct, json, random, subprocess, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from board_renderer import render_board, render_frame_wide
from PIL import Image as I

def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        # CI runners install ffmpeg with apt; no need to ship another binary
        import shutil
        exe = shutil.which("ffmpeg")
        if exe:
            return exe
        raise

# ---------------- music (randomized; every track is different) --------------------
PROGRESSIONS = [
    [[57,60,64,69],[53,57,60,65],[48,52,55,60],[55,59,62,67]],
    [[62,65,69,72],[57,60,64,67],[53,57,60,65],[55,59,62,66]],
    [[52,55,59,62],[57,60,64,67],[50,53,57,60],[48,52,55,59]],
    [[60,64,67,71],[65,69,72,76],[62,65,69,72],[67,71,74,77]],
    [[45,52,57,60],[41,48,53,57],[43,50,55,59],[48,55,60,64]],
    [[58,62,65,70],[51,55,58,63],[56,60,63,68],[53,57,60,65]],
]

# Short melodic shapes - the melody walks these instead of jumping to random
# chord tones, which is the difference between a tune and a beeping machine.
MOTIFS = [[0,1,2,1],[0,2,1,3],[2,1,0,1],[3,2,1,0],[0,1,3,2],[1,2,0,1]]
ARP = [0,1,2,3,2,1]          # eighth-note arpeggio over root-3rd-5th-octave

# Soft limiter. The signal is scaled so its peak lands on LIMIT_REF and then
# bent by x/(1 + KNEE|x|); 0 reference disables the limiter entirely.
LIMIT_REF = 1.6
LIMIT_KNEE = 0.55
# Feedback room (seconds), one delay per channel, and its decay.
ROOM_L, ROOM_R, ROOM_FB = 0.113, 0.137, 0.30

def make_music(path, seconds=75, sr=44100, rng=None, style="calm", gain=0.9):
    """One continuous STEREO piece for the WHOLE video.

    style="calm"  : the long-video bed - string pad, a piano motif, an
                     eighth-note arpeggio, sub bass and a soft kick/shaker,
                     with an energy arc that breathes every 8 chords so a
                     long track never flatlines into wallpaper.
    style="trend" : the Shorts bed - the same chord vocabulary but a driving
                     kick, off-beat hats, claps on 2 and 4 and a brighter
                     hook, so it reads as a hook inside the first second.

    Everything is synthesised from PROGRESSIONS below - no samples, no
    third-party audio - so every track is 100% original and copyright-free.
    Only key, tempo, motif and energy shape change per video, so no two
    uploads share a soundtrack.

    gain: peak level after normalisation (shorts sit quieter on purpose).
    """
    import random
    rng = rng or random.Random()
    key_shift = rng.choice([-5,-3,-2,0,2,3,5,7])
    chords = [[n + key_shift for n in ch] for ch in rng.choice(PROGRESSIONS)]
    steps = 8                              # eighth-notes per chord

    if style == "trend":
        beat = rng.choice([0.30, 0.34, 0.38])   # upbeat Shorts tempo
        g_pad, g_mel, g_arp = 0.040, 0.190, 0.070
        g_kick, g_hat, g_clap, g_bass = 0.42, 0.16, 0.24, 0.26
        root_oct, e_lo = -24, 0.86
    else:
        # The bed sits UNDER narration-less puzzle music: bright melody and
        # arpeggio lead, rhythm only supports. Bass and kick stay low so the
        # track does not collapse into sub-bass rumble.
        beat = rng.choice([0.55, 0.62, 0.7])    # unhurried long-video tempo
        g_pad, g_mel, g_arp = 0.045, 0.135, 0.065
        g_kick, g_hat, g_clap, g_bass = 0.11, 0.05, 0.06, 0.085
        root_oct, e_lo = -12, 0.72

    total = int(seconds * sr)
    # snap to a whole number of chords: the pad already fades in and out per
    # chord, so a whole-chord file loops seamlessly in ffmpeg (-stream_loop)
    # and a 12-minute bed costs one chord-loop to synthesise instead of 12
    # minutes of sample-by-sample Python.
    seg_len = int(steps * beat * sr)
    total = max(seg_len, -(-total // seg_len) * seg_len)
    L, R = [0.0] * total, [0.0] * total
    motif = MOTIFS[rng.randrange(len(MOTIFS))]
    vib_hz, vib_amt = rng.uniform(4.5, 5.5), 0.004

    def f(n): return 440.0 * 2**((n - 69) / 12.0)

    def put(i, v, pl=1.0, pr=1.0):
        if 0 <= i < total:
            L[i] += v * pl
            R[i] += v * pr

    def energy(ci):
        """Build over 8 chords then reset - keeps a long bed alive."""
        return e_lo + (1.0 - e_lo) * min(1.0, (ci % 8) / 5.0)

    # --- string pad: slow attack, vibrato, spread across the stereo field ---
    t0, ci = 0, 0
    while t0 < total:
        chord = chords[ci % len(chords)]
        for k, note in enumerate(chord):
            fr = f(note - 12)
            for j in range(min(seg_len, total - t0)):
                t = j / sr
                env = min(1, t/1.2) * min(1, (seg_len/sr - t)/1.5)
                vib = 1 + vib_amt*math.sin(2*math.pi*vib_hz*t)
                v = g_pad * env * (
                    math.sin(2*math.pi*fr*vib*t)
                    + 0.3*math.sin(2*math.pi*2.001*fr*t))
                put(t0 + j, v, 1.0, 0.80 + 0.06*k)
        t0 += seg_len; ci += 1

    # --- piano motif: one shaped phrase per chord, beats 1-4 ---------------
    t0, ci = 0, 0
    while t0 < total:
        chord = chords[ci % len(chords)]
        tones = [chord[0], chord[1], chord[2], chord[0] + 12]
        e = energy(ci)
        for m in range(4):
            fr = f(tones[motif[m] % 4] + 12)
            start = t0 + int(m * 2 * beat * sr)
            dur = int(rng.uniform(1.1, 1.7)*sr)
            for j in range(min(dur, total - start)):
                t = j / sr
                env = math.exp(-1.8*t)
                v = g_mel * e * env * (
                    math.sin(2*math.pi*fr*t)
                    + 0.5*math.sin(2*math.pi*2*fr*t)*math.exp(-2*t)
                    + 0.25*math.sin(2*math.pi*3*fr*t)*math.exp(-4*t))
                put(start + j, v, 0.9, 1.0)
        t0 += seg_len; ci += 1

    # --- arpeggio: eighth notes, panned right, the bed's sense of motion ---
    t0, ci = 0, 0
    while t0 < total:
        chord = chords[ci % len(chords)]
        e = energy(ci)
        for s in range(steps):
            fr = f(chord[ARP[s % len(ARP)]])
            start = t0 + int(s * beat * sr)
            dur = int(1.6 * beat * sr)
            for j in range(min(dur, total - start)):
                tt = j / sr
                v = g_arp * e * math.exp(-6.0*tt) * (
                    math.sin(2*math.pi*fr*tt)
                    + 0.35*math.sin(2*math.pi*2*fr*tt))
                put(start + j, v, 0.55, 1.0)
        t0 += seg_len; ci += 1

    # --- sub bass on the chord root, re-struck every quarter --------------
    step = int(beat * sr)
    t0, ci = 0, 0
    while t0 < total:
        root = f(chords[ci % len(chords)][0] + root_oct)
        e = energy(ci)
        for s in range(0, steps, 2):
            start = t0 + int(s * beat * sr)
            for j in range(min(2*step, total - start)):
                tt = j / sr
                env = min(1, tt/0.02) * math.exp(-1.6*tt)
                put(start + j, g_bass * e * env * math.sin(2*math.pi*root*tt))
        t0 += seg_len; ci += 1

    # --- percussion: kick every beat, shaker on the off-beat, clap on 2/4 --
    t0, ci = 0, 0
    while t0 < total:
        e = energy(ci)
        for s in range(0, steps, 2):                       # kick
            k0 = t0 + int(s * beat * sr)
            for j in range(int(0.14*sr)):
                if k0 + j >= total: break
                tt = j / sr
                fr = 78*math.exp(-22*tt) + 42
                put(k0 + j, g_kick*e*math.exp(-16*tt)*math.sin(2*math.pi*fr*tt))
            sh = k0 + step//2                              # shaker / hat
            for j in range(int(0.05*sr)):
                if sh + j >= total: break
                put(sh + j, g_hat*e*math.exp(-70*j/sr)*rng.uniform(-1, 1),
                    1.0, 0.5)
        if style == "trend":                               # clap on 2 and 4
            for s in (2, 6):
                c0 = t0 + int(s * beat * sr)
                for j in range(int(0.09*sr)):
                    if c0 + j >= total: break
                    put(c0 + j, g_clap*e*math.exp(-45*j/sr)*rng.uniform(-1, 1),
                        0.8, 0.8)
        t0 += seg_len; ci += 1

    # --- short stereo room: feedback combs, one delay per channel ---------
    # O(samples), no library needed, and it is what turns a dry synth stack
    # into something that sounds produced. Different times L/R for width.
    for buf, dt in ((L, ROOM_L), (R, ROOM_R)):
        d = int(dt * sr)
        if d:
            for i in range(d, total):
                buf[i] += ROOM_FB * buf[i - d]

    # --- soft limiter: the kick peaks would otherwise drag the whole track
    # down ~3 dB when we peak-normalise. Scale first so the knee sits at a
    # known place, then bend loud samples only; quiet parts pass untouched
    # and pick up a little harmonic warmth on the way through.
    if LIMIT_REF:
        peak0 = max(max(abs(v) for v in L), max(abs(v) for v in R)) or 1e-9
        sc = LIMIT_REF / peak0
        for i in range(total):
            a = L[i] * sc
            b = R[i] * sc
            L[i] = a / (1.0 + LIMIT_KNEE * abs(a))
            R[i] = b / (1.0 + LIMIT_KNEE * abs(b))

    # peak-normalise each channel -> predictable level, never clips
    peak = max(1e-9, max(max(abs(s) for s in L), max(abs(s) for s in R)))
    k = gain / peak
    with wave.open(path, "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(
            struct.pack("<hh",
                        int(max(-1, min(1, L[i] * k)) * 32000),
                        int(max(-1, min(1, R[i] * k)) * 32000))
            for i in range(total)))

# ---------------- frames ---------------------------------------------------------
def _mellow_bed():
    """The shared mellow pad from factory/make_music.py — the SAME song all
    three channels use. Chess plays it as the full soundtrack (mixed hot at
    the call sites), science/bio tuck it under the narration."""
    factory = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "factory"))
    if factory not in sys.path:
        sys.path.insert(0, factory)
    from make_music import ensure_bed
    return str(ensure_bed(Path(factory) / "assets" / "mellow_bed.wav"))


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
    music = _mellow_bed()   # shared seamless pad, ffmpeg tiles it for runtime
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
    subprocess.run([ff, "-y", "-f","concat","-safe","0","-i",lst,
        "-stream_loop","-1","-i",music,
        "-map","0:v","-map","1:a","-t",str(total),
        "-af","volume=2.5,alimiter=limit=0.95:attack=5:release=50,"
              "afade=t=out:st={:.1f}:d=2".format(total-2),
        "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
        "-c:a","aac", final],
        check=True, capture_output=True)
    for p in parts: os.remove(p)
    os.remove(lst)
    return final

def make_short(pz, out_dir, tag, i, ff=None, seg=15):
    """One puzzle -> vertical Short (9:16), static frame, its own random music."""
    os.makedirs(out_dir, exist_ok=True)
    sw, sh = 1080, 1920
    frame = board_frame(pz, i, out_dir, tag, sw, sh, suffix="s")
    music = _mellow_bed()
    final = os.path.join(out_dir, f"{tag}_short{i}.mp4")
    subprocess.run([ff, "-y", "-loop","1","-t",str(seg),"-i",frame,"-i",music,
        "-filter_complex", f"[0:v]scale={sw}:{sh},fps=25[v]",
        "-map","[v]","-map","1:a","-t",str(seg),
        "-af","volume=2.5,alimiter=limit=0.95:attack=5:release=50,"
              f"afade=t=out:st={seg-2}:d=2",
        "-c:v","libx264","-preset","veryfast",
        "-pix_fmt","yuv420p","-c:a","aac","-shortest", final],
        check=True, capture_output=True)
    os.remove(frame)
    return final

if __name__ == "__main__":
    ff = get_ffmpeg()
    demo = json.loads(open(os.path.join(HERE, "..", "puzzles_pool.jsonl"),
                           encoding="utf-8").readline())
    demo = [demo] * 5
    v = make_video(demo, os.path.join(HERE, "out"), "test", ff=ff)
    s = make_short(demo[0], os.path.join(HERE, "out"), "test", 1, ff=ff)
    print("OK:", v, "|", s)
