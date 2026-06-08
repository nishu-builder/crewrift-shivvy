#!/usr/bin/env bash
# Pull verbose logs + scores from our most recent LIVE league episodes, for
# remote debugging without re-running anything locally. Needs login (see
# scripts/submit.sh). Reads our own agent logs (the Shivvy verbose trace) and
# the ground-truth game event log for each episode.
#
# Usage: scripts/league-logs.sh [POLICY_NAME] [N_EPISODES]
set -euo pipefail
cd "$(dirname "$0")/.."

POLICY="${1:-shivvy}"
N="${2:-3}"
COWORLD_ID="cow_634f9b19-9bab-489b-af62-1e3623887640"
OUT="league-logs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

ids=$(uv run coworld episodes --mine --limit 1000 --json | python3 -c "
import sys, json
pol = '$POLICY'
cow = '$COWORLD_ID'
seen = []
for e in json.load(sys.stdin):
    if e.get('coworld_id') != cow or e.get('status') != 'completed':
        continue
    if any(pol in (p.get('policy_name') or '') for p in e.get('participants', [])):
        seen.append(e['id'])
print('\n'.join(seen[:$N]))
")

[ -z "$ids" ] && { echo "no completed league episodes found for policy '$POLICY'"; exit 0; }
for id in $ids; do
  echo "=== $id ==="
  uv run coworld episode-logs "$id" --mine --download-dir "$OUT/$id" || true
  uv run coworld episode-logs "$id" --game --download-dir "$OUT/$id" || true
done
echo "logs in $OUT"
