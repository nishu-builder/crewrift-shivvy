# Findings & future directions (handoff)

A running log of what we learned climbing Shivvy, what worked, what didn't, and
where to push next. Read this + `AGENTS.md` + `DIAGNOSIS.md` + `ITERATION.md`
before iterating. Numbers are from controlled XP runs vs the **same top-7 Daily
champions** (the rigorous A/B; see "Measurement" below) unless noted.

## TL;DR state (as of this handoff)

- Best version: **v7** — ~**81.7 mean, 74% win, 5/100 zero-games, 0 vote penalties**
  vs the top-7 field. Beats our notsus baseline (~69) and Andre's v8 (76.5 same roster).
- Version lineage (each builds on the previous):
  - v1: **vote failsafe** (never eat the −10 no-vote penalty) — the single biggest win.
  - v2/v3: **imposter** hunt-when-ready + kill-connect (pulse ButtonA + close to point-blank).
  - v4: nav-abandon + crew consensus voting — **both neutral/negative** vs field.
  - v5/v6: **aggressive "stalking" imposter** (shadow nearest crewmate on cooldown) — real win (zeros 14→6).
  - v7: v6 **minus consensus voting** — neutral vs v6, cleaner. **Current best.**
- Champion: our new versions (v4–v7) are stuck **disqualified/qualifying in a blocked
  Qualifiers round**, so they can't reach Daily yet. **v3 holds our live Daily slot.**
  When qualifying unblocks: `uv run python scripts/set_champion.py shivvy:v7`.

## What we learned (the important stuff)

1. **The −40 vote-penalty tail was the dominant baseline loss.** Stock notsus failed
   to cast a vote in ~10% of meetings → −10 each, up to −40/game. The failsafe
   (force a skip cast late in the timer) eliminated it (0% vs notsus's 7–12%). This
   is most of our gain over baseline. **Lesson: look for avoidable negative-score
   tails before chasing upside.**

2. **Imposter is a structurally losing role vs competent crews — for everyone.** We
   decoded replays of Andre's truecrew v5 AND v8 (he claimed v8 is "a very good
   imposter"): both get **1 kill/game and lose every time**, killing late (~+2000–2500
   ticks). v8's strength is its **crew** play (86 mean as crew) not imposter (10 as
   imposter). **There is no imposter secret sauce to copy.** Crews finish tasks before
   2 imposters can kill enough (need crew ≤ imposters = ~4 kills).

3. **Our aggressive stalking imposter beats the conservative meta.** Shadowing the
   nearest crewmate while on cooldown (so we're in range the instant it's ready)
   dropped zero-score games 14→5 and got occasional imposter *wins* in self-play —
   plausibly a better imposter than Andre's. Still 0 imposter wins vs the *elite*
   top-7, but fewer wipeouts.

4. **Top scores come from CREW play, not imposter.** Leaders sit ~79–82; the spread
   is mostly crew win-rate. We're at 74% crew wins. **The highest-EV frontier is
   probably squeezing crew win-rate, not imposter heroics.**

5. **Things that DIDN'T help (don't redo):**
   - Crew **consensus voting** (vote a ≥2-accuser target): neutral/slightly negative; rarely fires. Dropped in v7.
   - **nav-abandon** (give up unreachable tasks): fixes a real self-play freeze but it's too rare vs the field to move the mean.

6. **Field difficulty swings wildly across the day** (means ranged 50→82 as people
   upgraded bots). **Never trust the raw leaderboard for A/B** — a fresh champion's
   cumulative number reflects only the rounds it played. Always compare with a
   **matched XP run** vs a fixed roster.

7. **Scoring contract** (drives everything): win **+100**, task **+1**, kill **+10**,
   no-vote/no-skip **−10**, standing-still-with-tasks **−1/10s**. Winning dominates.

## Measurement (how to A/B rigorously)

- `uv run python scripts/xp_request.py <policy_version_id> -n 100` fires 100 episodes
  vs the top-7 Daily champions (explicit roster; works even while "qualifying").
- Pull scores by xreq: `GET /observatory/v2/experience-requests/<xreq_id>` → episodes[].scores,
  filter to your policy_version_id. (Key off policy_version_id, NOT coworld_id — the
  league uses a newer coworld than your local one.)
- Decode replays to study any bot's behavior: build `tools/expand_replay.nim` against the
  **latest** coworld-crewrift checkout (the replay hash must match the sim version), then
  `expand_replay <file.bitreplay>` prints Kill/BodyFound/Died/EnteredRoom/VoteCast/Chat with
  ticks. Replays are at episode `replay_url` (.json.z = zlib of a `.bitreplay`).
- Watch our own behavior: the verbose per-tick trace is baked into the image (policy logs);
  for live league episodes, `scripts/league-logs.sh`.

## Future directions (prioritized)

1. **Crew win-rate (highest EV).** This is where points live and where the leaders win.
   - Faster/optimal task routing (order tasks, avoid backtracking; current is nearest-task).
   - Don't die: as crew, avoid being the isolated victim (stick near groups) — fewer crew deaths = more task-wins.
   - Study the *leaders' crew* behavior via replay decode (we only studied imposters). What do
     Lively/alibi/truecrew crews do that wins more? (e.g., task efficiency, grouping, voting).
2. **Imposter that actually WINS (high ceiling, hard).** v5 gets kills but 0 imposter wins
   vs elites. To win you must thin crew below imposter count before tasks finish:
   - Kill every cooldown (we stalk now — verify kill *cadence* in replays).
   - Coordinate with the co-imposter (double-kills to swing the count fast).
   - Use **vents** to reach isolated victims / escape reports (we don't vent at all).
   - Kill task-doers to deny task progress (we prefer task-parked victims — measure if it helps).
3. **Crew social deduction done right.** Consensus voting was too weak. Higher-signal:
   detect **venting** (a player teleporting between non-adjacent rooms = proof of imposter)
   and vote them. Requires room-adjacency + per-player tracking. Zero false positives is key
   (voting out a crewmate is catastrophic).
4. **Re-measure cheaply, often.** Use xp_request.py for every change; matched roster; n=100.

## Gotchas / environment (save yourself time)

- **coworld>=0.1.20** required (earlier versions can't parse the server's image-upload
  response and break `upload-policy`). Pinned in pyproject.
- **No CLI command for XP requests or set-champion** (through 0.1.20) — use
  `scripts/xp_request.py` and `scripts/set_champion.py` (raw Observatory API).
- The Observatory POST endpoints (experience-requests, image upload) **flakily 404** while
  minting an id — **retry with backoff** (scripts already do).
- The engine repo (`Metta-AI/coworld-crewrift`) now **needs auth to clone**; the Dockerfile's
  in-build clone works only off a cached layer. **Bumping `CREWRIFT_ENGINE_REF` busts that and
  fails** — vendor a local authed clone + `COPY` it in if you must bump. We build against 0.1.39
  (`716fc42`); it runs fine in the live 0.1.40 league.
- **Fast inner loop:** native compile-check in ~3s (see ITERATION.md) before paying for the
  emulated amd64 Docker build.
- Champion state can look inconsistent (`is_champion` flag vs commissioner `substatus`) when a
  qualifying round is blocked.

## Key IDs

- League `league_605ff338-0a2e-4e62-aeda-559df9a9198f` · Daily div
  `div_8d3ead22-1244-49f5-8ee8-1bd150be2f6e` · Coworld `cow_634f9b19-...` (local 0.1.39;
  live league is on a newer cow_4012ebfa/0.1.40).
- Our player "Nishad"; control player "NishadIota" runs stock notsus (good A/B baseline).
- Top-7 opponent policy_version_ids are in `scripts/xp_request.py` history / the xreq notes.
