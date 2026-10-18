# BUILDLOG — everything built here, in one place

> Written 2026-10-19 (Tehran) so nothing is ever forgotten: what exists,
> why it is the way it is, what broke, and what is still pending.
> This file is the single source of truth for resuming work.

## The system

Three fully-automated YouTube channels — **1 video per channel per day,
without any machine online**:

| # | Channel | Account | Token file | Style |
|---|---------|---------|-----------|-------|
| 2 | Chess (puzzles) | Dazai Osamu | `yt_auth/chess_token.json` | board render, chiptune, NO captions |
| 1 | Science | secret_key | `yt_auth/sci_token.json` | stock footage + yellow captions |
| 3 | Biography | Arian Ensafnia | `yt_auth/bio_token.json` | stock footage + yellow captions |

Everything runs from `.github/workflows/` on GitHub Actions:

- **`daily.yml`** — crons `0 21 * * *` + `0 23 * * *` (UTC) and manual
  dispatch. Steps: system deps (apt **ffmpeg** — NOT preinstalled on
  runner images, this bit us once) → pip deps (`factory/requirements.txt`)
  → `daily_local.py` (renders + uploads all three channels) → chess
  thumbnail drip (continue-on-error) → commit state back (pull --rebase
  + push, 5 retries).
- **`bank-topup.yml`** — cron `0 3,15 * * *`, runs `gen_mass.py sci/bio
  --minutes 60` and commits fresh scripts back, so the banks grow toward
  10k/12k while nobody is around.

Runner tokens: `yt_auth/*.json` is gitignored; `daily_local.py`
materializes them at startup from env secrets (`CHESS_TOKEN_JSON`,
`SCI_TOKEN_JSON`, `BIO_TOKEN_JSON` — also `YT1_TOKEN_JSON`, `PEXELS_KEY`).

## The rules (non-negotiable, see AGENTS.md for subtitles)

- **1 post per channel per day** (`channels.py` → `daily_cap: 1`,
  spacing 6). An episode = long + shorts; the cursor only advances when
  EVERY slug of the episode is up, so days alternate long → short →
  long… nothing stalls, nothing double-posts.
- Quota: UTC day reset, ~10,000 units/day, an upload ≈ 1,600 →
  1/channel/day fits with headroom.
- Subtitle law: yellow `#FFD600` Arial Bold, black box 75% alpha,
  rounded, max 2 lines, y=79% landscape / 59% portrait, **never two
  captions in one frame** (sequential windows, GAP 0.04 s,
  `_verify_subs.py` counts overlaps).
- **Audio (added 2026-10-19):** every science/bio video gets a mellow
  pad loop (`factory/make_music.py` → `assets/mellow_bed.wav`, 32 s,
  pure-stdlib synthesis, no copyright) mixed at `volume=0.10`
  (≈ −20 dB under voice peaks) with `amix … normalize=0` so narration
  levels are bit-identical to before. Chess keeps its own chiptune.

## Push history lesson (the 408s)

Pushes failed with HTTP 408 because 70 MB `wiki_cache/` (5,845 files),
`puzzles_db.zst` (293 MB), `puzzles_pool_big.jsonl` (43 MB) rode every
pack. Fix: all gitignored, plus `topics_sci_old_generic.txt` and
`factory/content_chess_backup_*/`. Remaining big content goes up in
~400-file slices (`chunk_push` technique) — attempt-1 succeeds.

**.gitignore cuts `content_chess` at episode 2000.** So:
- On GitHub: episodes 1–1999 (≈ 21 years at 1/day).
- Local + Desktop backup zip only: episodes 2000–10010.
- If we ever want them on GitHub too: re-allow and push in slices.

## Runner bugs fixed (2026-10-18, in order)

1. No token files on runner → env-secret materialization in
   `daily_local.py`.
2. Thumb drip crashed on missing file → `continue-on-error: true`.
3. State push rejected "fetch first" → pull --rebase loop.
4. `ModuleNotFoundError: imageio_ffmpeg` (chess) → added to requirements.
5. `FileNotFoundError: 'ffprobe.exe'` (science/bio TTS probe — hardcoded
   Windows fallback) → `FFPROBE = shutil.which("ffprobe") or "ffprobe"` +
   apt ffmpeg in workflow.
6. `imageio-ffmpeg>=4.9` doesn't exist (max 0.6.0) → `>=0.5`.

Proof runs: `39094605834` (first full success, 47 min), bank-topup
`39093439646` + `39151459617` + `39167709692` (all success).

## Live uploads verified (oEmbed, 2026-10-18 UTC, all runner-made)

- chess: `mjdOCI5cYSw` — "12 Chess Puzzles: Clear the Square, Take the
  Game (Part 5)"
- science: `otXHrlusl0A` — "Nihilism — The Cold Version"
- bio: `rMhAhI98Xto` — "Joe Biden — The Journey That Made The Name"

Counts confirmed `2026-10-18 / count: 1` per channel — the daily cap
held.

## Banks (2026-10-19)

- science: 1,342 `factory/content/m*.json` (+ legacy scripts), target
  12,000 via bank-topup.
- bio: 290 `factory/content_bio/b*.json`, target 12,000.
- chess: 10,010 episodes total; 1,999 on GitHub, rest local-only
  (see above).

## NEW CHANNELS (Desktop deliverable)

`C:\Users\USER\Desktop\NEW CHANNELS\`:

- `10-ideas.md` — the full idea list.
- `01-TRUE-CRIME` (Isdal Woman / coldroom), `02-DARK-PSYCHOLOGY`
  (mindmanual), `03-WAR-HISTORY` (decisive) — each with concept.md +
  10-episode table + 2 sample scripts (long+short).
- `INSTAGRAM\plan.md` — handle **@manipulation.manual**, funnel plan.
  **Pending: account creation needs the owner's phone (SMS).**
- `sample_long.mp4/.jpg` + `sample_short.mp4/.jpg` per idea — rendered
  by `factory.py --render` (with the music bed).

## Pending / owner-blocked

1. **Instagram signup** — owner's phone for SMS verification.
2. **Custom thumbnails on science + bio** — YouTube returns 403 until
   the owner verifies a phone in YouTube Studio (Settings → Channel →
   Feature eligibility).
3. Optional: push chess episodes 2000+ to GitHub in slices.
4. Optional: give the new-channel ideas their own repos/tokens when
   they graduate from samples.

## Key files

- `factory/factory.py` — science/bio renderer (TTS → pexels → captions →
  assemble → **music mix** → thumbnail).
- `factory/chess_factory.py` + `bot/music_lib.py` + `bot/board_renderer.py`
  — chess (board frames, chiptune, shorts).
- `factory/daily_local.py` — runner entrypoint (caps, render, upload,
  manifest, state push).
- `factory/channels.py` — per-channel profiles: caps, spacing, manifests.
- `factory/gen_mass.py` — bank generator (`sci|bio --limit --minutes`),
  portable (REPO-relative).
- `factory/make_music.py` — mellow bed synth (stdlib only).
- `factory/_verify_subs.py`, `factory/_check_uploads.py` — QA tools.
- `factory/state/` — cursors, upload manifests, daily counts.
  **This directory is the dedupe authority; the runner commits it back.**

## Operator cheat-sheet

```powershell
gh workflow run daily-3channels -R Fyosamu/thumb-bot   # post now
gh workflow run bank-topup     -R Fyosamu/thumb-bot    # grow banks now
gh run list -R Fyosamu/thumb-bot                       # watch runs
python factory/_check_uploads.py                       # live-URL + bank check
python _verify_subs.py <slug>                          # caption overlap QA
```
