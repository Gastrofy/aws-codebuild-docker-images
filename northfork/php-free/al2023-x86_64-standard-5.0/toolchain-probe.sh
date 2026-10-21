#!/usr/bin/env bash
set -euo pipefail
bash --version | head -1
jq --version
python3 --version
python3 -m pip --version
python3 -c 'import ssl,json; print("python standard library OK")'
node --version
npm --version
aws --version
git --version
envsubst --version | head -1
ruby --version
go version
java -version 2>&1 | head -1
dotnet --version
docker --version
docker buildx version
