#!/usr/bin/env bash
# Build the Shivvy player image. The league requires linux/amd64, so we always
# build amd64 (emulated on Apple Silicon; the heavy dep layers are cached, so
# code-only rebuilds just rerun the compile layer).
#
# Fast inner loop: `nim c -d:botHeadless players/shivvy/shivvy.nim` inside a
# coworld-crewrift checkout catches compile errors in ~3s before you pay for a
# Docker build. See docs/ITERATION.md.
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="${1:-shivvy:dev}"
docker build --platform linux/amd64 -t "$IMAGE" .
docker image inspect "$IMAGE" --format 'built {{.RepoTags}} {{.Os}}/{{.Architecture}}'
