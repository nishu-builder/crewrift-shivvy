#!/usr/bin/env bash
# Run local CrewRift episodes with the Shivvy image and collect scores, replays,
# and the verbose policy logs. Downloads (and caches) the league Coworld, builds
# a full-config episode request, then runs N episodes.
#
# Usage:
#   scripts/scrim.sh [IMAGE] [N_EPISODES] [MAX_TICKS]
# Examples:
#   scripts/scrim.sh                       # shivvy:dev, 1 episode, full 10000 ticks
#   scripts/scrim.sh shivvy:dev 3 2500     # 3 quick episodes (2500 ticks each)
#
# Artifacts land in runs/<timestamp>/. Read the game event log and the per-agent
# verbose logs there. Watch a replay with scripts/replay.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="${1:-shivvy:dev}"
N="${2:-1}"
MAX_TICKS="${3:-}"
COWORLD_ID="cow_634f9b19-9bab-489b-af62-1e3623887640"
CACHE="coworld"

[ -d "$CACHE/$COWORLD_ID" ] || uv run coworld download "$COWORLD_ID" -o "$CACHE"
MANIFEST="$CACHE/$COWORLD_ID/coworld_manifest.json"

TICKS_ARG=()
[ -n "$MAX_TICKS" ] && TICKS_ARG=(--max-ticks "$MAX_TICKS")
uv run python scripts/make_episode_request.py "$MANIFEST" \
  --image "$IMAGE" "${TICKS_ARG[@]}" -o /tmp/shivvy_episode_request.json

OUT="runs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
uv run coworld scrimmage "$MANIFEST" /tmp/shivvy_episode_request.json \
  -n "$N" -o "$OUT" --timeout-seconds 1800

echo "=== artifacts in $OUT ==="
find "$OUT" -maxdepth 2 -name results.json -o -name '*.stdout.log' | sort | head
