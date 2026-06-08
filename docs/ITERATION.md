# Iterating on Shivvy

## Prerequisites

- Docker (the league requires `linux/amd64` images; on Apple Silicon they run
  emulated — fine, just slower).
- `uv` (drives the PyPI `coworld[auth]` CLI). Run `uv sync` once.
- For the *fast compile check* only: `nim` + `nimby` (the engine's toolchain).

## The loop

```bash
uv sync                                # once: install coworld[auth]
scripts/build.sh shivvy:dev            # build amd64 image (dep layers cached)
scripts/scrim.sh shivvy:dev 1          # one full episode (~4 min); use 3 2500 for quick noisy runs
scripts/replay.sh runs/<ts>/replay     # watch it in the viewer
# read runs/<ts>/logs/*  -> edit src/shivvy.nim -> repeat
```

### Fast inner loop (compile errors in ~3s, no Docker)

A Docker build is slow under emulation. To check that a Nim edit compiles before
building, compile natively against a local engine checkout:

```bash
git clone https://github.com/Metta-AI/coworld-crewrift /tmp/cr   # once
mkdir -p /tmp/cr/players/shivvy/shivvy
cp src/shivvy.nim /tmp/cr/players/shivvy/shivvy.nim
cp src/shivvy/*.nim /tmp/cr/players/shivvy/shivvy/
cd /tmp/cr && nimby --global sync nimby.lock                     # once
SDK=$(/usr/bin/xcrun --show-sdk-path)                            # macOS: real SDK, not the nix shim
nim c -d:release -d:botHeadless -d:useMalloc --opt:speed \
  --cc:clang --clang.exe:/usr/bin/clang --clang.linkerexe:/usr/bin/clang \
  --passC:"-isysroot $SDK" --passL:"-isysroot $SDK" \
  --out:/tmp/shivvy-native players/shivvy/shivvy.nim
```

This only verifies compilation (a macOS Mach-O binary can't run in the Linux
harness); the runnable artifact still comes from `scripts/build.sh`.

## Reading the logs

`scripts/scrim.sh` writes per-episode artifacts under `runs/<ts>/`:

- `logs/game.stdout.log` — **ground truth** from the engine: who connected, every
  `vote called` / `vote cast` / `vote ended`, kills, and the win line.
- `logs/policy_agent_N.log` — Shivvy's own view for slot N. Two parts:
  - **Play-phase trace** (added by us; on unless `NISHAD_VERBOSE=0`):
    ```
    [t=1234][lime][imposter] (812,640) mv=right | hunting red
    ```
    `t=`tick, color, role (`/ghost` when dead), `(x,y)` world pos, `mv=`input,
    then `bot.intent` — the single string the bot sets each frame, so this line
    narrates tasks ("precise task approach to ..."), navigation ("A* to ..."),
    imposter behavior ("hunting", "kill", "hard chase", "fake target", "imposter
    idle"), and death.
  - **Voting blocks** (`--- voting ---`): parsed players, chat, who voted, our
    chosen `vote target`, and the decision reason.
- `results.json` — final `scores`, `win`, `tasks`, `kills`, `imposter` per slot.

To find a bad game: grep `results.json` for low scores, then read that slot's
trace. A `-10`-style miss shows as a meeting in `game.stdout.log` with no
`vote cast: <our color>` line.

## Ship it

```bash
uv run softmax login          # once per machine
scripts/build.sh shivvy:latest
scripts/submit.sh shivvy:latest shivvy
```

## Debug the live league remotely (no local runs)

```bash
scripts/league-logs.sh shivvy 5     # pull our agent trace + game log for 5 recent league episodes
```

Because the verbose trace is baked into the image, live league episodes carry
the same per-tick narration — read them straight from `league-logs/<ts>/`.

## Measure a policy vs the live field on demand (XP request)

To run a controlled batch of a specific policy version against the real field
(not wait for live rounds), fire an experience request:

```bash
uv run python scripts/xp_request.py <requester_policy_version_id> -n 100
```

It POSTs the Observatory API directly (the CLI has no command for this) with the
requester + the top-7 Daily champions as an explicit 8-player roster. Works even
while the policy is still "qualifying". Then pull scores by filtering
`coworld episodes --mine --json` to that policy_version_id (the XP uses the
league's current canonical coworld, which may be newer than your local one — key
off the policy_version_id, not coworld_id).

## Refreshing the diagnosis numbers

```bash
uv run coworld results div_8d3ead22-1244-49f5-8ee8-1bd150be2f6e        # Daily leaderboard
uv run coworld submissions -l league_605ff338-0a2e-4e62-aeda-559df9a9198f --mine --json
uv run coworld episodes --mine --limit 1000 --json                     # filter coworld_id to crewrift, bucket scores
uv run coworld episode-stats <ereq_id> --json                          # per-player rewards for one episode
```

## Prioritized backlog

1. **Vote failsafe** (kills the `-40` tail). *Done* — `decideVotingMask` forces a
   SKIP cast past `VoteFailsafeTicks` (2/3 of the timer) and mashes confirm past
   `VotePanicTicks` (90%). Dormant in normal voting; confirm via `league-logs.sh`
   that live episodes no longer score `-40`.
2. **Imposter aggression** (biggest upside). *Done (v1)* — `imposterHuntActive`
   now returns true whenever `imposterKillReady`, so the imposter stops faking and
   hunts the moment a kill is available (previously it re-entered a 500-tick fake
   delay after every meeting). Self-play traces show both imposters now actively
   `hard chase`/`kill`. Kill-connect improved by pulsing `ButtonA` (edge-
   triggered, like vote confirm) and combining it with continued approach so an
   edge-of-`killRange` miss closes to point-blank and connects next frame --
   self-play now shows both imposters landing 2 kills and occasional imposter
   *wins*. Next: lower `ImposterHuntDelayTicks` for faster re-positioning,
   isolate victims, and use vents.
3. **Crew social deduction.** Track alibis / vent sightings / proximity-to-body
   and vote real imposters; never vote out a crewmate without strong evidence.
4. **Task routing.** Avoid oscillation; order tasks (nearest / simple TSP) to
   finish faster and dodge the standing-still penalty.

Always: change one capability, scrim, read the trace, confirm the intended
behavior changed and scores moved, then submit.
