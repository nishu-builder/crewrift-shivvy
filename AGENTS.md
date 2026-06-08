# AGENTS.md — continuing Shivvy

You are improving the Shivvy CrewRift player. **Start with `docs/FINDINGS.md`** —
the running handoff log of current state, what worked/didn't, and prioritized
future directions. Then `README.md`, `docs/DIAGNOSIS.md` (what's wrong and where
the points are), `docs/ITERATION.md` (the build/run/log/submit + XP loop), and
`docs/GAME.md` (rules and scoring contract). Keep `docs/FINDINGS.md` updated as
you learn.

## Working agreement

- **Always run it.** Build, scrim, and read the logs before claiming a change
  helps. One full episode is ~4 min; use shorter `maxTicks` for quick passes.
- **Evidence before and after.** Quote the metric you moved: per-slot
  `results.json` scores and the trace lines that prove the new behavior. The
  diagnosis bug is measured as "fraction of slots scoring `≤ -10`" and "imposter
  slots scoring `> 0`".
- **One capability at a time.** Change the vote failsafe *or* imposter hunting,
  not both, so the logs attribute the effect.
- **Never submit without explicit human approval** unless told otherwise. Submit
  with `scripts/submit.sh` only after local evidence beats the current entry.
- Keep changes in `src/shivvy.nim` (the brain). Touch `src/shivvy/protocols.nim`
  / `votereader.nim` only for protocol/parse fixes.

## Orientation in `src/shivvy.nim`

It is a large single-file bot forked from `notsus`. Key functions:

- `decideNextMask` — wrapper that calls `decideNextMaskInner` then `traceFrame`
  (our verbose play-phase logging). `bot.intent` is set everywhere inside and is
  what the trace prints — keep setting it on new branches so they stay visible.
- `decideNextMaskInner` — per-frame crewmate logic: bodies, button reset, tasks,
  navigation.
- `decideImposterMask` / `imposterHuntActive` / `attackVisibleCrewmate` —
  imposter play (see backlog item 2).
- `decideVotingMask` / `desiredVotingDecision` / `parseVotingScreen` — meetings
  and voting (see backlog item 1: the `-40` failsafe).
- `nearestTaskGoal` / `holdTaskAction` — task selection/completion.

## Engine dependency

We build against a pinned `coworld-crewrift` (`CREWRIFT_ENGINE_REF` in the
`Dockerfile`) and `bitworld`, fetched at build time — not vendored. If the env,
sprite protocol, action schema, or game config changes, bump that ref, rebuild,
re-scrim, and fix any compile/behavior breaks before submitting. Treat memory and
these docs as possibly stale — re-check live IDs, the leaderboard, and the config
(`docs/GAME.md`) before relying on them.

## Don'ts

- Don't add `try/except`-style error hiding; let it crash with a stack trace.
- Don't vendor the whole engine into this repo; keep it a pinned dependency.
- Don't commit secrets (login tokens). Auth is interactive via `softmax login`.
