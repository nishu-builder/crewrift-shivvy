# Findings & future directions (handoff)

A running log of what we learned climbing Shivvy, what worked, what didn't, and
where to push next. Read this + `AGENTS.md` + `DIAGNOSIS.md` + `ITERATION.md`
before iterating. Numbers are from controlled XP runs vs the **same top-7 Daily
champions** (the rigorous A/B; see "Measurement" below) unless noted.

## UPDATE 2026-06-08 (rigorous re-diagnosis vs current live field)

Pulled v7's full per-episode score distribution from real XP runs on the current
coworld (0.1.42) via the new `coworld xp-request` CLI (see Measurement). Two key
corrections to the picture below:

- **v7 is now the LIVE Daily champion.** Qualifying unblocked; v7 holds our Daily
  slot (`lpm_965c9446…`, membership champ=True). The "stuck in Qualifiers" note
  below is stale. No action needed to promote v7.
- **Crew is essentially maxed; the score gap is ALL imposter, and imposter is
  structurally dead vs this field.** v7's distribution (n=100, fixed top-7 roster):

  | score | n | meaning |
  |---|---|---|
  | 108 | 56 | crew win, all 8 tasks |
  | 107 | 14 | crew win, 7 tasks |
  | 106 | 4 | crew win, 6 tasks |
  | 10 | 19 | **imposter, exactly 1 kill, lost** |
  | 0 | 5 | imposter, 0 kills, lost |
  | 5,6 | 2 | crew loss (partial tasks) |

  → **crew win rate ≈ 97% (74/76)**, imposter win rate **0/24**. Field-wide,
  crew wins **98/100**, imposters **2/100**. The whole missing-points pool is the
  ~24% of games we draw imposter and score ~8 instead of ~108.

- **Why imposter is dead (verified in engine + traces):** `killCooldownTicks=900`,
  and **every meeting resets all imposters' cooldown to full 900**
  (`sim.nim` `applyVoteResult`). Crews preemptively press emergency buttons ("just
  resetting cooldowns") — with 6 crew × 1 button they can keep us on cooldown most
  of the game. Elite crews finish all ~48 tasks by **~t≈3200 of 10000**. Trace of a
  score-10 game: meetings at t≈700 and t≈1400 reset our cooldown, first window opens
  ~t2300, we kill once at t2451, then "hard chase" for a 2nd kill until **CREW WINS
  at t3169**. There is no early window (imposters start on a full cooldown, so first
  natural ready ~t1020 is already after the crew's first button). Both 0-kill and
  1-kill imposter games are lost the same way — not by being voted out, not by an
  execution bug. **More aggression/venting cannot beat a cooldown the crew controls.**

- **The one real (but hard) crew lever: ejecting imposters in the *harder* field.**
  Crew win rate is roster-dependent: the SAME v7 scored **81.7 vs an Andre-field but
  73.3 vs a Jernau-field** (one opponent swap = 8.4 mean). The drop is ~10 extra
  crew LOSSES (score 6/7) where a strong imposter out-kills the task race. In those
  losses we were **alive at the end, still doing tasks**, and **skipped every vote**
  ("vote target: unknown"): our crew deduction only fires on proximity-to-body or
  revenge, which rarely have signal. Converting those needs real social deduction
  (vent-sighting / witnessed-kill → eject), which is the only direction with upside
  left. Risk: a false-positive ejection of a crewmate is catastrophic.

- **Measurement noise floor is ±~8 mean at n=100** (roster composition dominates).
  Any A/B MUST use a *fixed* roster for baseline+candidate, and small imposter tweaks
  (which can't produce wins) are below this floor — compare the imposter/crew-loss
  *subset*, not just the overall mean. **Bottom line: v7 is at/near the field ceiling;
  the only positive-EV frontier is crew imposter-ejection, and it's hard + risky.**

## UPDATE 2026-06-08 (vent-detection built, validated, measured — INERT vs meta)

Per the "crew imposter-ejection" lever above, built **crew vent-sighting → eject**:
a crewmate that vanishes while standing on a vent that is comfortably inside our
view *must* have vented (players move ~3px/tick and can't leave the view that
fast) → mark them a confirmed imposter (`knownImposters`), chat-accuse, and
vote-eject. Code: `detectVentSightings` / `onVentCenter` / `worldInSafeView` +
`knownImposterVotingTarget` / `maybeQueueVentAccusation` in `src/shivvy.nim`
(uploaded as **shivvy:v9**, pv `f154e659…`).

- **Validated end-to-end.** With a temporary `-d:ventTest` build making our own
  imposters vent, self-play crew detected them and the game log showed
  "<color> killed by vote" — detect→accuse→vote→eject works.
- **Caught a real bug first:** the sprite view is only **128×128 px**; an initial
  `VentViewMargin=96` made the safe-view window empty so the detector could
  *never* fire. Fixed to 40 (must be < 64 = half-screen).
- **Zero false positives** across ~44k agent-frames of non-venting self-play
  (margin 40). Safe: it only ever votes a player it is certain vented.
- **But it's INERT vs the current field.** A clean n=100 A/B on the current
  roster: v9 **77.9** vs v7 **76.8** (within the ±~6.6 noise floor; crew-loss
  12→11, field imp-wins 17→16 — no real change). Log scan: **VENT SIGHTING fired
  in 1/100 episodes** (that one was a crew win). The meta bots (notsus / alibi /
  crewborg / suspectra variants) **almost never vent**, and from our local camera
  we almost never witness it. The lever is real but meta-dependent and currently
  near-dead.
- **Decision: v9 NOT championed** (no proven gain). The code is kept as a
  correct, safe, latent capability that would pay off only if the meta shifts to
  venting imposters. To revisit, widen witnessing (appear-at-vent, looser margin)
  — but expect FP risk and still-rare opportunity.
- **League restructured mid-session:** the division renamed Daily→"Competition"
  and our v7 shows `disqualified` there (old champions appear to need
  re-qualification). Re-entering our best policy is a separate submit/qualify
  step (left for a human call). The XP-vs-policy_version_id path still works
  regardless of division state.

## UPDATE 2026-06-09 (qualifier wedge ROOT-CAUSED: champion-in-staging bug; v11 re-queued)

Why v11 sat unselected in Qualifiers for ~10h while the commissioner cycled
Richard's submissions (read straight from app_backend v2 source in the m1 repo):

- **The champion endpoint strands staging memberships.** `promote_league_policy_
  membership_to_champion` unconditionally sets `status=competing`, but qualifier
  rounds only select memberships with `status=qualifying`
  (`v2/membership_filters.py::division_entrants`). Our `set_champion.py shivvy:v11`
  call (on its Qualifiers membership) flipped it `qualifying→competing` — invisible
  to the commissioner forever. Field-wide, 4 policies were stranded the same way
  (incl. Andre's truecrew:v12 and notsus:v3). **Never champion a membership until
  it is IN Competition.**
- **Unblock = retire + re-submit.** Re-submission of a pv with an active membership
  is rejected (`v2/pipeline.py` "already has an active membership"), so:
  `coworld retire-membership <lpm_id>` then `coworld submit shivvy:v11 --league …`.
  Done 2026-06-09 ~17:40Z: v11 now `qualifying` (lpm_40c0232d…). Qualifier rounds
  run every ~10 min and need only 1 qualifying entrant; each completed round
  promotes its entrants to Competition with substatus=champion.
- **Competition is dormant league-wide since ~10:00Z, separately.** Rounds need
  `minimum_champions=8` champions; only 1 exists (suspectra v33) after the
  disconnect-penalty wave disqualified everyone. Empty leaderboard for all players.
  Not fixable from our side; flagged to Andre via Discord DM with both diagnoses.
- Richard's loop explained: he keeps submitting new versions (→v52); each fresh
  submission is a `qualifying` membership that gets the next round and promotes.
  There was never a commissioner preference for him — just nobody else in the
  `qualifying` state.

## UPDATE 2026-06-09 (reconnect fix proven live; disconnect issue filed upstream; META SHIFTED)

- **Reconnect fix validated in production.** shivvy:v10 (exit-on-first-disconnect) took
  exactly -100 three times in its last Competition round (`round_813cc7f1`) — the
  disqualification pattern. shivvy:v11 played the first post-recovery round
  (`round_0d3c713a`, 162 episodes) with **zero negative scores**, and a fresh n=20 XP run
  had 20/20 single-connect clean game-over exits (no drops observed on the k8s XP path).
- **Upstream default player analyzed + issue filed:**
  [Metta-AI/coworld-crewrift#43](https://github.com/Metta-AI/coworld-crewrift/issues/43).
  Server grace is 30s (`sim.nim DisconnectTimeoutTicks = TargetFps*30`, penalty -100);
  upstream notsus now reconnects (`exitOnDisconnect` hardcoded false) but only for
  `ReconnectWindowMs = 8s` and with no game-over detection — it gives up 22s before the
  server would, and burns the full window even on normal post-game closes.
- **THE META SHIFTED (task-distance normalization + stronger imposters).** Same-day n=20
  XP vs an active roster: mean **38.95** — 12/20 crew LOSSES (5-8 pts), and **2 imposter
  WINS (120 = win + 2 kills)**. The "crew ~97% win / imposter structurally dead" ceiling
  diagnosis above is **stale**: imposters now win regularly field-wide, and crew-loss
  prevention (deduction/ejection, survival) is suddenly the dominant score lever. v11's
  league mean is drifting down (75.8 -> 73.1, rank 2 -> 6 as rounds accumulate). Next
  session: re-run the full diagnosis (role/outcome decomposition, per-loss traces) before
  touching strategy — the optimization target has changed under us.

## UPDATE 2026-06-09 (NEW-META DIAGNOSIS, n=20 fixed-roster + engine source + per-tick logs)

Full re-diagnosis after the meta shift. Evidence: xreq_d177f9ac (n=20, k8s, active
roster), all 20 of our per-tick logs mined, current engine source read (latest
coworld-crewrift main).

**Rule changes that flipped the game:**
- `KillCooldownTicks` 900 -> **500**. Meetings still reset imposter cooldowns, but each
  reset now only buys 500 ticks; the crew button-lockout is ~2x weaker. Imposters won
  **14/20** episodes field-wide (was ~2%).
- Ejections are EXTINCT vs this field: **0 ejections in 20 games**. Our vent detector
  fired twice (meta bots vent now), we chat-accused in field lingo ("Pink sus" x11,
  delivered) and voted the confirmed imposter — nobody bandwagons, everyone skips.
  Deduction has no payoff until the field starts voting sus targets.
- **Ghosts can do tasks** (engine `applyGhostMovement` has the full task block;
  `completeTask` pays +1 and counts toward the task win; `totalTasksRemaining` counts
  dead crews' tasks). Our bot already task-grinds as a ghost — correct, keep.
- Crew win is now a pure RACE: 4 crew deaths (~t2200-4400 at current kill cadence) vs
  all 48 tasks (crew wins land ~t3500-4200).

**Our n=20 decomposition (mean 38.95):** crew 4/16 wins (25%, was ~97%) with losses
worth ~6.5; imposter 2/4 WINS (was 0% — stalking + cooldown 500 is now lethal). The
whole deficit is crew losses; +25% crew win rate ~= +19 mean. Imposter is fine.

**Ranked strategy changes (crew, in order of expected value):**
1. **FIX BUG: endgame "localized, no task goal" stall.** In 6/16 crew games (4 losses,
   2 wins) the bot idles from t~3000 with 1-3 server-incomplete tasks left —
   `nearestTaskGoal` only targets *visible* task icons and there is no exploration
   fallback when icons aren't in the local mirror (also: tasks interrupted at hold~1 by
   a meeting look locally done but aren't). Fix: when own incomplete tasks remain
   (score-derived or via re-check) and no icon is visible, patrol known task stations.
   Direct +1-3 pts/game; in the 2 long losses (end t>4100) those tasks plausibly
   blocked `allTasksDone` — ~100-pt swings.
2. **Button timing.** We burn our single emergency button at t~420-560 in EVERY game —
   same moment as the rest of the field (early chat is full of "just resetting imposter
   cool downs"), so resets overlap and waste lockout coverage. Hold ours for the
   mid/late game (e.g. after 2 crew deaths, or when estimated imposter-ready time
   arrives and no meeting happened recently): one well-timed press denies a full
   500-tick kill window exactly when the race is decided. Note a meeting also
   teleports everyone home (interrupts tasks) — net EV needs the A/B.
3. **Task throughput.** Wins finish our 8 tasks by t~2966-3564; the fastest loss ended
   t2172 (unwinnable on tasks). Shave idle/interstitial ticks and plan around the
   home-teleport after every meeting (pick post-meeting tasks near home first).
4. **Don't build more deduction for now** (keep the free vent detector). Re-check
   monthly: if the field ever starts bandwagoning votes, ejection + ghost-tasks
   becomes the dominant win path overnight.

**Measurement:** n>=100 fixed-roster A/B per change; compare crew-loss subset and own
task count, not just the mean (+-8 noise floor).

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

- **The CLI now has native XP support** (newer coworld): `coworld xp-request
  create|list|get|episodes`. Prefer it over the raw-API scripts.
  - `scripts/xp_request.py` still works (it fires vs a **pinned** fixed roster now,
    not whatever order the API returns — required for a clean A/B). Note the API
    changed shape: `policy_version_id` is gone; the id is nested under
    `policy_version.id`. The script was fixed for this 2026-06-08.
  - `uv run coworld xp-request get <xreq_id> --json` returns `episodes[]` each with
    `participants` (position→policy_version/label) and `scores` ([{policy_version_id,
    score}]). Filter scores to OUR `policy_version_id` (v7 =
    `7f261793-f682-4618-963a-3d4c83036241`). Key off policy_version_id, NOT
    coworld_id — the league runs a newer coworld (0.1.42+) than your local one.
- **Use a FIXED roster** (same 7 opponents for baseline and candidate); roster
  composition swings the mean by ~8 (see UPDATE above). The pinned roster lives in
  `scripts/xp_request.py` (`PINNED_ROSTER`).
- **Decompose by role/outcome, don't just read the mean.** Crew win ≈ 106–108,
  imposter ≈ 0/10/20 (kills×10), crew loss ≈ partial tasks (5–8). Imposter win rate
  vs this field is ~0, so for imposter changes compare the *sub-100 subset* (or pull
  per-agent logs via `coworld episode-logs <ereq_id> --mine --download-dir <d>` and
  grep `[imposter]`/`[crewmate]` to label role exactly). Field imposter-win check:
  count players scoring ≥100 per episode (6 ⇒ crew win, 2 ⇒ imposter win).
- `coworld episode-logs <ereq_id> --mine -d <dir>` downloads OUR verbose per-tick
  trace for any XP episode (rotate_seats means our slot varies per episode) — this is
  how the imposter/crew-loss diagnoses above were made, no replay decode needed.
- Decode replays to study any bot's behavior: build `tools/expand_replay.nim` against the
  **latest** coworld-crewrift checkout (the replay hash must match the sim version), then
  `expand_replay <file.bitreplay>` prints Kill/BodyFound/Died/EnteredRoom/VoteCast/Chat with
  ticks. Replays are at episode `replay_url` (.json.z = zlib of a `.bitreplay`).
- Watch our own behavior: the verbose per-tick trace is baked into the image (policy logs);
  for live league episodes, `scripts/league-logs.sh`.

## Future directions (prioritized) — REVISED 2026-06-08

The 2026-06-08 re-diagnosis overturns the old "crew win-rate / faster task routing"
priority. Crew is ~maxed and task routing / not-dying-as-crew are negligible (we win
≈97%; we keep the +100 even when we die before finishing, so unfinished tasks cost
only 1–2 pts). Imposter heroics are also dead (crews hard-counter kills via
cooldown-resetting emergency buttons; 0/24 imposter wins). What's left:

1. **Crew imposter-ejection (only positive-EV lever; hard, risky).** In the harder
   field (strong imposters), ~10% of games are crew losses where we're alive, skipping
   every vote. Add a **zero-false-positive** deduction signal and eject:
   - **Vent-sighting**: we already parse vent positions (`bot.sim.vents`). Track each
     visible player's position frame-to-frame; a player that vanishes at / appears from
     a vent is *definitely* an imposter. Accuse via chat + vote them.
   - **Witnessed kill**: directly seeing X adjacent to Y the instant Y becomes a body.
   - Risk: a false-positive ejection of a crewmate flips a win to a loss — keep the bar
     at *proof*, never suspicion (chat-consensus voting already tested neutral/negative).
   - Caveats: fires only when we witness it (rare), and 1 vote rarely ejects (need the
     elite bots to bandwagon our chat accusation). Measure on a *fixed hard roster*,
     compare the crew-loss subset, likely need n>100 to clear the ±8 noise floor.
2. **Accept v7 as the ceiling.** Honest option: v7 ≈ field ceiling (81.7 vs a field
   where the best established bots sit 77–80). Further gains are small + noisy.
3. **(Dead ends — don't redo)** imposter kill-cadence / vents-for-killing / co-imposter
   coordination (co-imposter is an opponent in XP) / faster task routing / not-dying-as-crew.
4. **Re-measure cheaply, often.** `coworld xp-request` (or `scripts/xp_request.py`);
   FIXED roster; decompose by role; n≥100.

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
