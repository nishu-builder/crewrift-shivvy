"""Decompose paired XP runs by role/outcome for an A/B verdict.

Usage:
  uv run python scripts/ab_analyze.py <label>=<xreq_id> <label>=<xreq_id> ...

Labels each run, filters scores to our requester policy_version, and prints
mean, role/outcome decomposition, and the crew-loss subset comparison the
FINDINGS.md measurement protocol calls for.
"""

from __future__ import annotations

import json
import subprocess
import sys
from statistics import mean


def classify(score: float) -> str:
    if score >= 100:
        return "imposter win" if score >= 110 else "crew win"
    if score in (0.0, 10.0, 20.0, 30.0) :
        return "imposter loss"
    if score < 0:
        return "penalty"
    return "crew loss"


def main() -> None:
    for arg in sys.argv[1:]:
        label, xreq = arg.split("=", 1)
        raw = subprocess.run(
            ["uv", "run", "coworld", "xp-request", "get", xreq, "--json"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        d = json.loads(raw)
        requester_pv = d["episodes"][0]["participants"][0]["policy_version_id"]
        ours: list[float] = []
        field_imp_wins = 0
        for ep in d["episodes"]:
            winners = sum(1 for s in ep["scores"] if s["score"] >= 100)
            if winners == 2:
                field_imp_wins += 1
            for s in ep["scores"]:
                if s["policy_version_id"] == requester_pv:
                    ours.append(s["score"])
        kinds: dict[str, list[float]] = {}
        for sc in ours:
            kinds.setdefault(classify(sc), []).append(sc)
        n = len(ours)
        crew_n = len(kinds.get("crew win", [])) + len(kinds.get("crew loss", []))
        imp_n = len(kinds.get("imposter win", [])) + len(kinds.get("imposter loss", []))
        print(f"=== {label} ({xreq[:18]}…) n={n} ===")
        print(f"mean {mean(ours):.2f} | field imposter-win episodes {field_imp_wins}/{len(d['episodes'])}")
        for kind in ("crew win", "crew loss", "imposter win", "imposter loss", "penalty"):
            scores = kinds.get(kind, [])
            if not scores:
                continue
            denom = crew_n if kind.startswith("crew") else imp_n
            print(
                f"  {kind:13} n={len(scores):3} ({100 * len(scores) / denom:.0f}% of role)"
                f" mean={mean(scores):7.2f}"
            )
        low = [s for s in ours if 0 < s < 100 and s <= 6]
        print(f"  crew losses scoring <=6: {len(low)}")
        print()


if __name__ == "__main__":
    main()
