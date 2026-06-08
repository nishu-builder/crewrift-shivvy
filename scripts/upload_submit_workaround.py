"""Upload + submit a policy, working around a broken CLI upload path.

As of the 0.1.40 rollout the server changed the image-upload contract: the
/observatory/v2/container_images/upload response now returns
pre_signed_info.authorization_token (an ECR docker-login token) instead of
pre_signed_info.credentials, which the published coworld CLI (<=0.1.19) requires
-- so `coworld upload-policy` fails with a pydantic ValidationError and ALL
uploads via the CLI are broken. authorization_token IS exactly the auth header
the CLI builds from the old credentials (b64("AWS:password")), so we push with it
directly and reuse the rest of the CLI's flow. Delete this once the CLI is fixed.

Usage: uv run python scripts/upload_submit_workaround.py [IMAGE] [NAME]
"""

from __future__ import annotations

import subprocess
import sys
import tempfile

from coworld.upload import (
    CoworldUploadClient,
    _image_upload_name,
    _local_image_client_hash,
    _push_archive_to_registry,
)

SERVER = "https://softmax.com/api"
LEAGUE = "league_605ff338-0a2e-4e62-aeda-559df9a9198f"


def main() -> None:
    image = sys.argv[1] if len(sys.argv) > 1 else "shivvy:latest"
    name = sys.argv[2] if len(sys.argv) > 2 else "shivvy"

    with CoworldUploadClient.from_login(server_url=SERVER) as client:
        client_hash = _local_image_client_hash(image)
        r = client._http_client.post(
            "/v2/container_images/upload",
            headers=client._headers(),
            json={"name": _image_upload_name(image), "client_hash": client_hash},
            timeout=60.0,
        )
        r.raise_for_status()
        d = r.json()
        img = d["image"]
        ps = d.get("pre_signed_info")
        if ps is not None:
            auth = ps["authorization_token"]  # already b64("AWS:password")
            base_url = f"https://{ps['registry']}/v2/{ps['repository']}"
            print(f"pushing {image} -> {ps['registry']}/{ps['repository']}:{ps['tag']}")
            with tempfile.TemporaryFile() as ar:
                subprocess.run(["docker", "image", "save", image], check=True, stdout=ar)
                ar.seek(0)
                _push_archive_to_registry(ar, base_url, ps["tag"], auth)
            client.complete_image_upload(img["id"])
        result = client.complete_docker_image_policy(
            name=name, container_image_id=img["id"], run=["/bin/shivvy"], secret_env=None
        )
        print(f"uploaded {result.name}:v{result.version} | policy_version_id={result.id}")
        sub = client.submit_to_league(LEAGUE, result.id)
        print(f"submitted to league: {sub}")


if __name__ == "__main__":
    main()
