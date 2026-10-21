#!/usr/bin/env bash
set -euo pipefail
docker info --format '{{.ServerVersion}}'
docker buildx version
mkdir -p /tmp/proof-context
printf '%s\n' 'proof' > /tmp/proof-context/proof
printf '%s\n' 'FROM scratch' 'COPY proof /proof' > /tmp/proof-context/Dockerfile
docker build -t sanitized-builder-daemon-proof /tmp/proof-context
test "$(docker image inspect sanitized-builder-daemon-proof --format '{{len .RootFS.Layers}}')" -eq 1
printf '%s\n' 'Docker daemon/buildx/build proof passed'
