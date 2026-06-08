"""Elect one of our policies as league champion from the terminal.

The coworld CLI can *view* champions (`coworld memberships --mine
--champions-only`) and retire memberships, but has NO set-champion command
(confirmed through 0.1.20), so we POST the Observatory endpoint directly:
POST /observatory/v2/league-policy-memberships/{id}/champion.

The champion is the policy that represents your player in a division's live
rounds. Gotcha: setting a Qualifiers-only membership as champion pulls you OFF
the Daily leaderboard until it qualifies — so this prefers the Daily membership
and warns if only a Qualifiers one exists.

Usage:
  uv run python scripts/set_champion.py            # list our memberships + champion
  uv run python scripts/set_champion.py shivvy:v6  # elect shivvy:v6 (Daily) as champion
"""

from __future__ import annotations

import sys

import httpx
from coworld.api_client import _load_current_cogames_token

BASE = "https://softmax.com/api"
LEAGUE = "league_605ff338-0a2e-4e62-aeda-559df9a9198f"


def my_memberships(headers: dict[str, str]) -> list[dict]:
    d = httpx.get(
        f"{BASE}/observatory/v2/league-policy-memberships",
        params={"league_id": LEAGUE, "mine": "true", "limit": 200},
        headers=headers,
        timeout=30,
    ).json()
    return d.get("entries", d) if isinstance(d, dict) else d


def label(m: dict) -> str:
    return (m.get("policy_version") or {}).get("label", "?")


def main() -> None:
    headers = {"Authorization": f"Bearer {_load_current_cogames_token(server_url=BASE)}"}
    members = my_memberships(headers)

    if len(sys.argv) < 2:
        print(f"{'POLICY':28} {'DIVISION':12} {'STATUS':12} CHAMPION  MEMBERSHIP")
        for m in members:
            div = (m.get("division") or {}).get("name", "?")
            champ = "CHAMPION" if m.get("is_champion") else ""
            print(f"{label(m):28} {div:12} {m.get('status',''):12} {champ:9} {m.get('id')}")
        return

    want = sys.argv[1]
    matches = [m for m in members if label(m) == want or (m.get("policy_version") or {}).get("id") == want]
    if not matches:
        sys.exit(f"no membership found for '{want}'")
    daily = [m for m in matches if (m.get("division") or {}).get("name") == "Daily"]
    target = daily[0] if daily else matches[0]
    div = (target.get("division") or {}).get("name")
    if div != "Daily":
        print(f"WARNING: '{want}' has no Daily membership (only {div}); electing it will "
              f"remove our Daily presence until it qualifies.")
    mid = target["id"]
    r = httpx.post(f"{BASE}/observatory/v2/league-policy-memberships/{mid}/champion", headers=headers, timeout=30)
    r.raise_for_status()
    print(f"elected {want} ({div}) as champion: is_champion={r.json().get('is_champion')}")


if __name__ == "__main__":
    main()
