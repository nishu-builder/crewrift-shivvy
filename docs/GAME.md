# CrewRift: rules, scoring, config

CrewRift is an *Among Us*-style social-deduction game. 8 players spawn; 2 are
secretly imposters. Crewmates do tasks and try to vote out imposters; imposters
fake tasks, kill, and use vents. Players are controlled over a WebSocket using
the **Bitworld Sprite v1** protocol — the bot sees the same sprite stream a human
would (no privileged state) and sends D-pad / button / chat inputs.

## Win conditions

- **Crew win:** all tasks completed, or all imposters voted out.
- **Imposter win:** imposters reduce the crew until `crew <= imposters`.

## Scoring (this is what the leaderboard ranks)

| Event | Points |
|---|---|
| Win the game | **+100** |
| Complete a task | +1 |
| Kill a crewmate (imposter) | +10 |
| **Not voting and not skipping in a meeting** | **−10** |
| Standing still while you still have tasks | −1 per 10 seconds |

A clean crewmate win is therefore `+100 + 8 = 108` (8 tasks). The league score
is the **mean round score** (`rules.division_leaderboard.source_score =
mean_round_score`); each round runs 100 episodes with ≥100 per entrant.

Implications that drive strategy:
- The `−10` no-vote penalty is the sharpest avoidable loss. Always cast *something*
  (even skip) before the timer. Four missed meetings = `−40`, observed often.
- Winning dominates the score (`+100`), so reliably finishing as a winning crewmate
  matters more than clever-but-risky votes. Don't vote out crewmates.
- Imposter value (`+10`/kill, `+100` win) is mostly unclaimed by baselines — see
  the button-reset meta below.

## Default game config (the "default" variant / live league)

```
players: 8            imposterCount: 2         tasksPerPlayer: 8
maxTicks: 10000       gameOverTicks: 360       killCooldownTicks: 900
startWaitTicks: 120   roleRevealTicks: 120     killRange: 20   reportRange: 20
voteTimerTicks: 240   voteResultTicks: 72      taskCompleteTicks: 72
ventRange: 16         buttonCalls: 1 (emergency button, once per player)
map: data/croatoan.resources
```

`coworld run-episode <manifest>` alone uses a **smoke fixture** (`maxTicks=300`)
that ends in an instant draw with zero scores — useless for tuning. Always run
the full variant via `scripts/scrim.sh` (which builds the episode request from
the `default` variant). See docs/ITERATION.md.

## The emergency-button meta

`killCooldownTicks=900` is long, and pressing the emergency button resets
imposter kill cooldowns. notsus crewmates exploit this: they repeatedly call
emergency meetings "just resetting imposter cool downs," which can keep an
imposter from ever getting a kill window. In all-notsus games imposters score 0.
Beating this as an imposter (early kills before the button spam, isolating a
victim, venting) is the main source of unclaimed points.

## Protocol

Sprite v1: <https://github.com/Metta-AI/bitworld/blob/master/docs/sprite_v1.md>.
Our parsing lives in `src/shivvy/protocols.nim` (frame decode, input/chat
encode) and `src/shivvy/votereader.nim` (vote-screen reader). The engine's game
constants and types come from `src/crewrift/sim` at build time.
