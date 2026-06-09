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

# A fixed strong roster (7 established top-of-Daily champions, by policy_version
# id) so every A/B compares against the *same* opponents. Resolved 2026-06-08
# from the Daily leaderboard. Override with --opponents to use a different field.
PINNED_ROSTER = {
    "Richard Higgins": "8663d329-7a36-4968-a534-091b3595d25d",  # crewrift-suspectra-richard:v18
    "James Bond": "5ac20e88-73e1-4c1d-8d0e-84aebc622e75",  # crewborg:v15
    "Jernau": "7d482931-b962-456c-99de-3d793116ed72",  # jernau-crewrift:v13
    "James Boggs": "c4443a86-0a3b-4667-a0d5-30820ef305bc",  # crewborg:v9
    "RelhAlpha": "34413cf7-6f78-450f-a633-5b81943413e1",  # crewrift-notsus-relhalpha:v4
    "slava2": "fe0f068c-763c-45b7-a301-f327cd6c80d6",  # tmp-notsus-alibi:v1
    "Andrew Brower": "95906f0a-1d61-41df-a47c-cee91686b8ae",  # monofuel-notsus:v1
}


def daily_champions(headers: dict[str, str]) -> list[tuple[str, str]]:
    d = httpx.get(
        f"{BASE}/observatory/v2/league-policy-memberships",
        params={"league_id": LEAGUE, "champions_only": "true", "active_only": "true", "limit": 100},
        headers=headers,
        timeout=30,
    ).json()
    entries = d if isinstance(d, list) else d.get("entries", [])
    out = []
    for m in entries:
        if (m.get("division") or {}).get("name") != "Daily":
            continue
        # The API nests the id under policy_version now (top-level
        # policy_version_id is gone), so read it from there.
        pv = (m.get("policy_version") or {}).get("id")
        out.append(((m.get("player") or {}).get("name"), pv))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("requester_policy_version_id")
    ap.add_argument("-n", "--num-episodes", type=int, default=100)
    ap.add_argument("--opponents", default="", help="Comma-separated policy_version_ids (default: top 7 Daily champions).")
    ap.add_argument("--execution-backend", default="k8s", choices=["k8s", "antfarm"])
    args = ap.parse_args()

    headers = {"Authorization": f"Bearer {_load_current_cogames_token(server_url=BASE)}", "Content-Type": "application/json"}
    if args.opponents:
        opponents = args.opponents.split(",")
    else:
        opponents = [pv for pv in PINNED_ROSTER.values() if pv != args.requester_policy_version_id][:7]
    if len(opponents) != 7:
        sys.exit(f"need exactly 7 opponents, got {len(opponents)}")

    payload = {
        "target": {"league_id": LEAGUE},
        "requester": {"policy_version_id": args.requester_policy_version_id},
        "opponents": [{"policy_version_id": o} for o in opponents],
        "num_episodes": args.num_episodes,
        "rotate_seats": True,
        "notes": "self-served via scripts/xp_request.py",
        "execution_backend": args.execution_backend,
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
