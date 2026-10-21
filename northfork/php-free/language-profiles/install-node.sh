#!/usr/bin/env bash
set -euo pipefail
version=$1
architecture=$2
archive_sha=$3
case "$architecture:$(uname -m)" in amd64:x86_64|arm64:aarch64) ;; *) exit 1 ;; esac
if [ "$archive_sha" != cached ]; then
    test "$architecture" = amd64
    archive="node-v${version}-linux-x64.tar.xz"
    curl --fail --silent --show-error --location --retry 3 --proto '=https' \
        "https://nodejs.org/dist/v${version}/${archive}" -o /tmp/node-profile.tar.xz
    printf '%s  %s\n' "$archive_sha" /tmp/node-profile.tar.xz | sha256sum --check -
    mkdir -p "/usr/local/n/versions/node/${version}"
    tar -xJf /tmp/node-profile.tar.xz --strip-components=1 -C "/usr/local/n/versions/node/${version}"
    rm /tmp/node-profile.tar.xz
fi
# A missing cached version fails. Never resolve a major, latest, or lts alias.
n --offline --no-preserve "$version"
test "$(node --version)" = "v${version}"
npm --version
