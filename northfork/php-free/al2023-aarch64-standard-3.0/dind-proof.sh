#!/usr/bin/env bash
set -euo pipefail
docker info --format '{{.ServerVersion}}'
docker buildx version
mkdir -p /tmp/proof-context
printf '%s\n' 'proof' > /tmp/proof-context/proof
printf '%s\n' 'FROM scratch' 'COPY proof /proof' > /tmp/proof-context/Dockerfile
docker buildx build --load --metadata-file /tmp/proof-metadata.json -t sanitized-builder-daemon-proof /tmp/proof-context
python3 -c 'import json; d=json.load(open("/tmp/proof-metadata.json")); assert d["containerimage.digest"].startswith("sha256:"); print("Buildx metadata Python JSON proof passed")'
test "$(docker image inspect sanitized-builder-daemon-proof --format '{{len .RootFS.Layers}}')" -eq 1
printf '%s\n' 'Docker daemon/buildx/build proof passed'
