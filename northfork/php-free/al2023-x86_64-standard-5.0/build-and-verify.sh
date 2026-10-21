#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
test "$(uname -m)" = x86_64
python3 - <<'PY'
import hashlib,json,pathlib
p=json.loads(pathlib.Path('provenance.json').read_text())
files={name:pathlib.Path(name).read_bytes() for name in p['frozen_files_sha256']}
assert all(hashlib.sha256(body).hexdigest()==p['frozen_files_sha256'][name] for name,body in files.items())
assert hashlib.sha256(b''.join(name.encode()+b'\0'+body for name,body in sorted(files.items()))).hexdigest()==p['frozen_package_sha256']
PY
docker build --progress plain -t ci-builder-proof:validated .
base_image=$(python3 -c 'import json;print(json.load(open("base-config.json"))["image"])')
docker run --rm --network none --entrypoint bash -v "$PWD/toolchain-probe.sh:/tmp/probe.sh:ro" "$base_image" /tmp/probe.sh > base-tools.txt
docker run --rm --network none --entrypoint bash -v "$PWD/toolchain-probe.sh:/tmp/probe.sh:ro" ci-builder-proof:validated /tmp/probe.sh > candidate-tools.txt
diff -u base-tools.txt candidate-tools.txt
python3 verify-candidate.py
container_id=$(docker run -d --privileged -v "$PWD/dind-proof.sh:/tmp/dind-proof.sh:ro" ci-builder-proof:validated bash /tmp/dind-proof.sh)
trap 'docker rm -fv "$container_id" >/dev/null 2>&1 || true' EXIT
test "$(docker wait "$container_id")" = 0
docker logs "$container_id"
