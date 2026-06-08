#!/usr/bin/env bash
# Open the replay viewer for a local scrimmage replay artifact or a league
# replay URL (the .json.z links from `coworld episodes --json`).
# Usage: scripts/replay.sh runs/<timestamp>/replay
set -euo pipefail
cd "$(dirname "$0")/.."
COWORLD_ID="cow_634f9b19-9bab-489b-af62-1e3623887640"
MANIFEST="coworld/$COWORLD_ID/coworld_manifest.json"
REPLAY="${1:?usage: scripts/replay.sh <replay path or URL>}"
uv run coworld replay "$MANIFEST" "$REPLAY"
