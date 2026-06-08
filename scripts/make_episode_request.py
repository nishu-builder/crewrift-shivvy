"""Build a full-config CrewRift episode request that runs our image.

`coworld run-episode <manifest>` alone uses the certification *smoke* fixture
(maxTicks=300 -> instant draw, zero scores). The real league variant runs
maxTicks=10000. This emits an episode_request.json pinned to a chosen variant
with our player image in the requested slots, so local episodes match league
conditions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from coworld.certifier import build_manifest_episode_job_spec, load_coworld_package


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--image", required=True, help="Our player image, e.g. shivvy:dev")
    ap.add_argument("--run", default="/bin/shivvy", help="argv[0] inside the image")
    ap.add_argument("--variant", default="default")
    ap.add_argument("--max-ticks", type=int, default=None, help="Override maxTicks for quicker iteration.")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument(
        "--slots",
        default="all",
        help="Comma-separated slot indices to fill with our image, or 'all'. "
        "Other slots keep the manifest's bundled player (notsus).",
    )
    ap.add_argument("-o", "--out", type=Path, default=Path("episode_request.json"))
    args = ap.parse_args()

    package = load_coworld_package(args.manifest)
    spec = build_manifest_episode_job_spec(package, variant_id=args.variant)
    req = spec.model_dump(by_alias=True)

    slot_count = len(req["players"])
    targets = range(slot_count) if args.slots == "all" else [int(s) for s in args.slots.split(",")]
    for i in targets:
        req["players"][i]["image"] = args.image
        req["players"][i]["run"] = [args.run]

    if args.max_ticks is not None:
        req["game_config"]["maxTicks"] = args.max_ticks
    if args.seed is not None:
        req["game_config"]["seed"] = args.seed

    args.out.write_text(json.dumps(req, indent=1))
    print(
        f"wrote {args.out}: variant={args.variant} maxTicks={req['game_config']['maxTicks']} "
        f"seed={req['game_config'].get('seed')} ours_in_slots={list(targets)} image={args.image}"
    )


if __name__ == "__main__":
    main()
