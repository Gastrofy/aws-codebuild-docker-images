#!/usr/bin/env bash
set -euo pipefail
# Custom CodeBuild images do not execute their image ENTRYPOINT.
# Keep an existing healthy daemon; otherwise start the bundled official daemon.
if ! docker info >/dev/null 2>&1; then
    test -x /usr/local/bin/dockerd-entrypoint.sh
    timeout 75 /usr/local/bin/dockerd-entrypoint.sh true
fi
docker info >/dev/null
printf '%s\n' 'CODEBUILD_DOCKER_DAEMON_READY'
