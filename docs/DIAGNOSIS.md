# Why notsus ranks low (and where the points are)

Evidence gathered from the live league API and local self-play. Re-run the
queries in [ITERATION.md](ITERATION.md) to refresh these numbers.

## Standing (Daily division snapshot)

Both of our original entries were stock `notsus`, near the bottom of 15:

```
 1  Alex Smith       82.39   Lively:v4            (social deduction)
 2  slava2           79.55   tmp-notsus-alibi
 9  Richard Higgins  75.51   notsus variant
14  NishadIota       74.17   nishadiota.notsus:v2   <- ours
15  Nishad           69.37   nishad.notsus:v1       <- ours (stock notsus)
```

Mean episode score by policy across ~560 of our sampled episodes (directional,
not the official mean_round_score): leaders `tmp-notsus-alibi` 107, `Lively` 106,
`Paz-Bot-9000` 95, `softmax-sussyboi` 90, `truecrew` 85; ours ~71–77. The
top names are all social-deduction variants; plain notsus is mid-pack.

## Problem 1 — the `-40` vote tail (avoidable)

NishadIota's per-episode scores are **bimodal**:

```
 [-50,-25): 50      <- exactly -40: four meetings × -10 "did not vote and did not skip"
 [  0, 25): 73      <- losses, no penalty
 [ 75,125): 363     <- wins (~108)
```

Confirmed on a real episode via `episode-stats`: **6 of 8 players scored 108 and
NishadIota scored −40.** notsus *tries* to vote — it parses the vote screen from
pixels, walks a cursor with momentum-controlled D-pad presses, then presses A —
but under harder conditions (the vote grid shrinks as players die, timing vs
other bots) it sometimes fails to cast before `voteTimerTicks=240`. Each miss is
`-10`. Killing this tail is pure downside removal worth several mean points.

**Fix direction:** a hard failsafe in the voting path — if we are on a vote
screen and have not registered a cast by a safe fraction of the timer, force a
SKIP cast (always legal for a crewmate). See `decideVotingMask` /
`desiredVotingDecision` in `src/shivvy.nim`.

## Problem 2 — imposter passivity (unclaimed upside)

In a full 10000-tick self-play episode (all-Shivvy), the result was a clean crew
win: six crewmates at 108, and **both imposters scored 0 — zero kills all game.**
The imposter logic (`decideImposterMask` → `imposterHuntActive` →
`attackVisibleCrewmate`) only kills when hunting is active *and* a crewmate is
visible *and* `imposterKillReady` *and* within `killRange=20`. Two things starve
it: `ImposterHuntDelayTicks=500` delays hunting, and crewmates spam the emergency
button to reset kill cooldown (six meetings in that game, all "just resetting
imposter cool downs"). Whenever we draw imposter (~25% of games) we score ~0 and
lose.

**Fix direction:** get early kills before the button-reset spam (lower the hunt
delay, prioritize an isolated victim right after role reveal), and don't waste
the kill window. Each kill is `+10` and an imposter win is `+100`.

## Problem 3 — weak social deduction as crew (smaller)

notsus only votes a target if it literally saw someone next to a body or got a
revenge vote; otherwise it skips. In self-play crew usually wins on tasks anyway,
but against mixed fields, actually identifying and voting out imposters (alibi /
vent / proximity-to-body tracking, like the `alibi`/`Lively`/`truecrew` leaders)
converts losses into wins.

## Net

Priority order: (1) eliminate the `-40` tail, (2) make the imposter actually
kill, (3) sharpen crew voting. (1) is cheap and safe; (2) is the biggest upside;
(3) is the path to the top. The verbose trace (ITERATION.md) is what lets you see
which of these is failing in any given game.
