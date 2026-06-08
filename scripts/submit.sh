#!/usr/bin/env bash
# Upload the Shivvy image as a Coworld policy and submit it to the Crewrift
# Daily league. Requires a fresh login first (interactive, one time per machine):
#     uv run softmax login
#
# Usage: scripts/submit.sh [IMAGE] [POLICY_NAME]
#   IMAGE        local amd64 image to upload (default shivvy:latest)
#   POLICY_NAME  league policy name        (default shivvy)
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="${1:-shivvy:latest}"
NAME="${2:-shivvy}"
LEAGUE="league_605ff338-0a2e-4e62-aeda-559df9a9198f"

uv run coworld upload-policy "$IMAGE" --name "$NAME" --run /bin/shivvy
uv run coworld submit "$NAME" --league "$LEAGUE" --no-open-browser
echo "submitted $NAME to $LEAGUE"
