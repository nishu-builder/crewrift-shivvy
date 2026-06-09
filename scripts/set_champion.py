"""Elect one of our policies as league champion from the terminal.

The coworld CLI can *view* champions (`coworld memberships --mine
--champions-only`) and retire memberships, but has NO set-champion command
(confirmed through 0.1.20), so we POST the Observatory endpoint directly:
POST /observatory/v2/league-policy-memberships/{id}/champion.

The champion is the policy that represents your player in a division's live
rounds. Gotcha (root-caused 2026-06-09): championing flips the membership to
status=competing, but qualifier rounds only select status=qualifying entrants —
so championing a Qualifiers-only membership PERMANENTLY strands it. This script
now refuses that; champion only after promotion to Competition.

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
    # Prefer the live competition membership (a competing, non-Qualifiers slot) so
    # we champion the entry that actually appears on the leaderboard. Fall back to
    # whatever exists (e.g. a still-qualifying Qualifiers membership) otherwise.
    def rank(m: dict) -> int:
        div = (m.get("division") or {}).get("name") or ""
        live = m.get("status") == "competing" and div != "Qualifiers"
        return (0 if live else 1, 0 if div != "Qualifiers" else 1)

    target = sorted(matches, key=rank)[0]
    div = (target.get("division") or {}).get("name")
    if div == "Qualifiers" or target.get("status") != "competing":
        sys.exit(
            f"REFUSING: '{want}' is only in {div} (status {target.get('status')}). "
            f"Championing flips the membership to status=competing, and the qualifier "
            f"commissioner only selects status=qualifying entrants — this PERMANENTLY "
            f"strands the policy in Qualifiers (root-caused 2026-06-09; unblock was "
            f"retire-membership + re-submit). Wait for promotion to Competition, then re-run."
        )
    mid = target["id"]
    r = httpx.post(f"{BASE}/observatory/v2/league-policy-memberships/{mid}/champion", headers=headers, timeout=30)
    r.raise_for_status()
    print(f"elected {want} ({div}) as champion: is_champion={r.json().get('is_champion')}")


if __name__ == "__main__":
    main()
