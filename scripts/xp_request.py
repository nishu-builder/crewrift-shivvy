"""Self-serve a Coworld experience request (XP run) against the live field.

The `coworld` CLI has no command for this, so we POST the Observatory endpoint
directly (discovered from /api/observatory/openapi.json:
POST /observatory/v2/experience-requests, body V2CreateExperienceRequestRequest).

Notes learned the hard way:
- Requester and opponents must be given by `policy_version_id`; player names are
  ambiguous (a player has many policy versions) and league `top_n` selection
  404s with a requester. So we resolve the field's Daily *champions* explicitly.
- The roster must be exactly 8 players (requester + 7 opponents).
- The endpoint is flaky: it intermittently 404s while minting a fresh id. Retry.
- Works even while the requester policy is still "qualifying" (it's referenced
  directly by id), so you can measure a new submission before it reaches Daily.

Usage:
  uv run python scripts/xp_request.py <requester_policy_version_id> [-n 100]
  # default opponents = top 7 Daily champions excluding the requester
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx
from coworld.api_client import _load_current_cogames_token

BASE = "https://softmax.com/api"
LEAGUE = "league_605ff338-0a2e-4e62-aeda-559df9a9198f"


def daily_champions(headers: dict[str, str]) -> list[tuple[str, str]]:
    d = httpx.get(
        f"{BASE}/observatory/v2/league-policy-memberships",
        params={"league_id": LEAGUE, "champions_only": "true", "active_only": "true", "limit": 100},
        headers=headers,
        timeout=30,
    ).json()
    out = []
    for m in d.get("entries", []):
        if (m.get("division") or {}).get("name") != "Daily":
            continue
        out.append(((m.get("player") or {}).get("name"), m.get("policy_version_id")))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("requester_policy_version_id")
    ap.add_argument("-n", "--num-episodes", type=int, default=100)
    ap.add_argument("--opponents", default="", help="Comma-separated policy_version_ids (default: top 7 Daily champions).")
    args = ap.parse_args()

    headers = {"Authorization": f"Bearer {_load_current_cogames_token(server_url=BASE)}", "Content-Type": "application/json"}
    if args.opponents:
        opponents = args.opponents.split(",")
    else:
        opponents = [pv for _, pv in daily_champions(headers) if pv and pv != args.requester_policy_version_id][:7]
    if len(opponents) != 7:
        sys.exit(f"need exactly 7 opponents, got {len(opponents)}")

    payload = {
        "target": {"league_id": LEAGUE},
        "requester": {"policy_version_id": args.requester_policy_version_id},
        "opponents": [{"policy_version_id": o} for o in opponents],
        "num_episodes": args.num_episodes,
        "rotate_seats": True,
        "notes": "self-served via scripts/xp_request.py",
    }
    for attempt in range(6):
        r = httpx.post(f"{BASE}/observatory/v2/experience-requests", headers=headers, json=payload, timeout=90)
        if r.status_code == 200:
            d = r.json()
            print(f"created {d['id']} | {d['episode_count']} episodes | status {d['status']}")
            return
        print(f"attempt {attempt}: {r.status_code} {r.text[:140]}")
        time.sleep(3)
    sys.exit("failed after retries")


if __name__ == "__main__":
    main()
