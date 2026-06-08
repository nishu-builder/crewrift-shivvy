# Shivvy — a CrewRift player

Shivvy is our entry for the **Crewrift Daily** Softmax league. CrewRift is a
non-copyright-infringing *Among Us*: 8 players, 2 imposters, tasks, meetings,
voting, and betrayal. This repo is self-contained — our bot source, a build that
pins the CrewRift engine as a dependency, a local play/replay loop, and the
submit + remote-log tooling — so you can keep hill-climbing the policy.

- **League:** `league_605ff338-0a2e-4e62-aeda-559df9a9198f` (Crewrift Daily)
- **Coworld:** `cow_634f9b19-9bab-489b-af62-1e3623887640`
- Engine pinned in the `Dockerfile` (`CREWRIFT_ENGINE_REF`); CLI from PyPI `coworld[auth]`.

## Origin & current standing

Shivvy starts as a fork of `notsus`, the stock Nim baseline. As of the first
investigation our two stock-notsus entries sat **14th and 15th of 15** in the
Daily division. The two diagnosed reasons notsus is mediocre — and our roadmap —
are in [docs/DIAGNOSIS.md](docs/DIAGNOSIS.md):

1. **The `-40` vote tail.** ~10% of games score exactly `-40` = four meetings ×
   `-10` "did not vote and did not skip." notsus's pixel-based vote-screen
   navigation sometimes fails to cast before the timer. Pure, avoidable loss.
2. **Imposter passivity.** In a full self-play game both imposters scored **0** —
   they never killed. Whenever we draw imposter (~25% of games) we forfeit.

## The loop (4 commands)

```bash
uv sync                                  # install coworld[auth] from PyPI
scripts/build.sh shivvy:dev              # build the amd64 player image
scripts/scrim.sh shivvy:dev 1            # run a full local episode (~4 min)
scripts/replay.sh runs/<timestamp>/replay   # watch it
```

Then read `runs/<timestamp>/logs/` — the verbose per-agent trace (see
[docs/ITERATION.md](docs/ITERATION.md)) tells you what each Shivvy did every
tick. Edit `src/shivvy.nim`, rebuild, repeat. Ship with `scripts/submit.sh`.

## Layout

```
src/shivvy.nim          our bot (the brain): perception, nav, tasks, voting, imposter play
src/shivvy/protocols.nim    sprite-protocol parsing + input/chat encoding (forked)
src/shivvy/votereader.nim   vote-screen pixel reader (forked)
Dockerfile              fetches pinned coworld-crewrift + bitworld, overlays src/, compiles
pyproject.toml          uv project; CLI = PyPI coworld[auth]
scripts/                build / scrim / replay / submit / league-logs helpers
docs/FINDINGS.md        START HERE to continue: current state, what worked/didn't, next directions
docs/GAME.md            rules, scoring, full game config
docs/DIAGNOSIS.md       why we rank low, with evidence
docs/ITERATION.md       the dev loop (build/scrim/replay/submit/XP), log format, backlog
AGENTS.md               how an AI agent should continue this work
scripts/xp_request.py   measure a policy vs the live field (raw API; no CLI command exists)
scripts/set_champion.py elect/list champions (raw API; no CLI command exists)
```

We depend on the CrewRift engine (`src/crewrift/*`, `bitworld`) as a pinned
*library* at build time; it is not vendored here. Bump `CREWRIFT_ENGINE_REF` in
the `Dockerfile` to adopt a new engine/protocol version.
