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
- **Audio (added 2026-10-19):** ALL three channels play the same mellow
  pad loop (`factory/make_music.py` → `assets/mellow_bed.wav`, 32 s,
  pure-stdlib synthesis, no copyright, seamless tiling):
  - science/bio: mixed at `volume=0.10` (≈ −20 dB under voice peaks) with
    `amix … normalize=0` so narration levels are bit-identical to before —
    pure background, never tiresome.
  - chess: plays the bed as its FULL soundtrack, `volume=2.5` capped by
    `alimiter=limit=0.95` → measured mean −26 dB / peak −0.9 dB: clearly
    audible and warm, no clipping. The old chiptune generator
    (`music_lib.make_music`) is now unused but kept for reference.

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

## Local backup + cleanup (2026-10-19)

Owner asked for a tidy system: everything OpenCode produced outside the
live repo is wiped, but first a backup was taken —

- `C:\Users\USER\Desktop\BACKUP-thumb-bot-2026-10-19.zip` — code,
  workflows, banks (incl. chess 2000+ which exists ONLY locally),
  state/manifests, tokens, BUILDLOG.
- `C:\Users\USER\Desktop\BACKUP-NEW-CHANNELS-2026-10-19.zip` — the 3
  concepts, scripts, plan and the 6 sample renders.

Deleted on purpose (all regenerable): `%TEMP%\opencode\`, `%TEMP%\gh_*`
logs, `factory/work/`, `factory/out/`, `factory/_musictest.py`,
`factory/_sample_src/`, `wiki_cache/`, `puzzles_db.zst`. KEPT:
`puzzles_pool*.jsonl` (runtime input), topic lists, all banks,
`yt_auth/`, `_check_uploads.py` (QA tool, committed).

## Two new self-running factories (2026-10-19)

**A. webads — 10k ad videos, 1 Instagram reel/day (channel-independent).**

- `projects/webads/` — `concept.md`, `ad-copy.md` (FA+EN, "$1000 and up"),
  `pinterest-brief.md`, `gen_scripts.py` (10,000 scripts, ~70 words each,
  EN voice `en-US-AvaMultilingualNeural`, 7 scenes ≈30s), `make_thumb.py`
  (6 custom templates, height-adaptive text), `reel_robot.py`
  (date-index reel pick from `bank.jsonl`, renders via `factory.py --render`,
  uploads nothing — output ships as the `daily-reel` artifact).
- `.github/workflows/webads-reel.yml` — cron `0 14 * * *`, artifact
  `daily-reel` (mp4 + jpg, nothing mp4 committed).
- Verified: run **39178839281** SUCCESS — ep291, stat template, 7 segs,
  30.7s, mellow bed at 0.10 under the voice, custom thumb, 2m30s total.

**B. pdrip — rip-translate robot, 1 upload/day on new channel 4, forever.**

- `projects/pdrip/` — `robot.py`: discover → sanitize personal info →
  FA→EN sentence-exact translate → rebuild copyright-free through
  `factory.py --channel 4` → source-style thumbnail (Persian text on the
  original poster replaced by English) → `upload.py channel 4` (own token,
  cap 1) → state in `projects/pdrip/state/processed_pd.json`.
- Discovery story: YouTube is bot-walled from runners (yt-dlp 7 clients,
  transcript API `RequestBlocked`, Piped/Invidious dead, SEs unreliable),
  so the robot went **Aparat-first**: `GET /api/fa/v1/video/video/search/text/<q>/?type_search=search`
  (real topical results, ZWNJ must be stripped or the endpoint answers 400),
  `.../show/videohash/<hash>` for pre-signed CDN files (144p audio source),
  sitemap probing as safety net. Local proof: 8 real PD candidates
  (TEDx Amirkabir, نیک‌درس کمال‌گرایی, MBSR talks).
- Whisper path: `faster-whisper small int8`, HF cache restored by
  `actions/cache/restore` + saved `if: always()` (plain cache@v4 never
  writes on a failed job — exactly when the model is freshly pulled).
  **`av` pinned `<19`** — av 19.0.1 removed `metadata_errors`, which
  faster-whisper still passes → `TypeError` (run 39189278908).
- `.github/workflows/pd-daily.yml` — cron `30 14 * * *`, optional
  `YTDLP_COOKIES` secret re-enables YouTube, state commit `if: always()`
  with rebase-retry push. Upload line stays dormant until the owner mints
  the token: `python factory/get_token.py 4 pd` →
  `gh secret set PD_TOKEN_JSON < yt_auth/pd_token.json`.
- Runs: 39178845701/39179425977/39180401644/39183077628/39183895979
  (pre-aparat no-ops), 39189278908 (av-19 crash, fixed), 39189838070
  (first full end-to-end attempt).

## Multichan — 100 personal-development channels (2026-10-19)

The fleet expansion: 100 category channels (ids 5..104) on the same
rip-translate-rebuild machinery as channel 4, one video/day each,
engineered so 100x1/day renders fit GitHub's free tier **once the repo
is public** (private = 2000 min/month ≈ 3-4 channels; public = unlimited).
Nothing runs - or costs a cent of minutes - until a channel has a token.

- `projects/multichan/gen_channels.py` → `channels.json`: 25 categories
  (habits, goals, psychology, mindfulness, stoicism, career, reading…)
  x 4 channels = 100 unique names, Persian aparat queries per category,
  EN description, palette, rotating edge-tts voice (4 voices).
- `make_brand.py` → `brands/`: 2560x1440 banner + 800x800 avatar per
  channel (19.4 MB, gitignored here) — published to the **public
  `Fyosamu/brands` repo** so YouTube can fetch them by URL:
  `raw.githubusercontent.com/Fyosamu/brands/main/<id>_banner.jpg` (live,
  HTTP 200).
- `factory/channels.py` auto-registers ids 5..104 from the registry
  (own folders `content_m<n>/out_m<n>/work_m<n>`, own ledgers, token env
  `YT<n>_TOKEN_JSON`); `get_token.py <5..104>` mints + prints the exact
  `gh secret set` line.
- `projects/pdrip/robot.py --channel <n>`: discovery switches to that
  category's queries, TTS to that channel's voice, render/upload under
  that profile. ZWNJ is stripped before the aparat search API (400
  otherwise); state file stays shared so one source video feeds exactly
  one channel, ever.
- `.github/workflows/multichan.yml`: cron `0 13 * * *` → prep job reads
  `state/active_channels.json` → dynamic matrix (max 20 parallel) →
  per channel: branding (once, recorded per channel), robot, whisper
  cache, union state commit with 8 push retries. Empty active list =
  the whole wave costs one ~30s job.
- `set_brand.py`: title + description + keywords + banner via
  `channels.update`, recorded in `state/branded_m<n>.json` so a manual
  Studio edit is never overwritten afterwards.

## Operator cheat-sheet

```powershell
gh workflow run daily-3channels -R Fyosamu/thumb-bot   # post now
gh workflow run bank-topup     -R Fyosamu/thumb-bot    # grow banks now
gh run list -R Fyosamu/thumb-bot                       # watch runs
python factory/_check_uploads.py                       # live-URL + bank check
python _verify_subs.py <slug>                          # caption overlap QA
```

## 2026-10-20 � multichan: fleet channel 5 (Vanta Mind) E2E
- New Cloud project **mindseries-fleet** (innate-entry-512120-s2, aryn82674): YouTube Data API v3 enabled,
  OAuth consent "MindSeries Fleet" (External/Testing), **aryn82674 added as test user** (Testing mode blocks
  even the owner otherwise - access_denied decoded to test-user wall).
- Fleet client: 976930622070-3doq... (yt_auth/fleet_client.json, no BOM). Old client 712282483181 = Testing wall,
  unusable for new accounts without test-user adds.
- Channel created: **Vanta Mind @? / UCtlDMTc7wfyArTSw5KqThHA** (name Vanta Mind; @vantamind taken -> handle
  chosen from YouTube suggestion at creation time; token minted via localhost:8090 PKCE).
- Secret YT5_TOKEN_JSON set via **stdin pipe** (PS --body arg mangles embedded quotes; CRLF from file pipe
  breaks GITHUB_ENV). Single-line compact JSON = the only safe form.
- active_channels schema = {"channels": [5]} (bare [5] silently -> empty matrix).
- Run history: 39341219535 empty-matrix (schema), 39341474535 GITHUB_ENV CRLF, 39342273704 json quote mangling,
  39342736693 = first full attempt (branding + pdrip robot + upload).
- Banner/profile for id5 live on Fyosamu/brands (raw 200). Avatar (Google account photo) still pending -
  myaccount photo tile click no-ops + studio.youtube.com shows generic error in automation browser.

## 2026-10-20 - fleet channel 5 LIVE end-to-end
- Run 39342736693 SUCCESS: branding step + full robot (source Aparat -> translate -> render -> upload).
- Video live: https://www.youtube.com/watch?v=Mnsk21LO4b4 (10:42 long, public, tags set).
- Branding: description + keywords applied via brandingSettings (part=snippet is NOT updatable on
  channels - ERROR_PART_UNEXPECTED; part=brandingSettings must be the ONLY part). Title stuck at
  "Vanta Mind" because personal channel titles follow the Google account name (rename account =
  Keystone Habits to apply). Banner silently dropped by API on the new channel - readback warns.
- pdrip: description hashtags expanded, pd_thumb upgraded (2-line stroke title + accent bar).
- Repo flipped PUBLIC: runner minutes now unlimited; token files gitignored (verified clean).
