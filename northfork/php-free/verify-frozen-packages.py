#!/usr/bin/env python3
"""Verify the exact source packages used by the recorded native builds."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
for profile in ['al2023-x86_64-standard-5.0', 'al2023-aarch64-standard-3.0']:
    path = root / profile / 'provenance.json'
    provenance = json.loads(path.read_text())
    files = {name: (path.parent / name).read_bytes() for name in provenance['frozen_files_sha256']}
    for name, body in files.items():
        assert hashlib.sha256(body).hexdigest() == provenance['frozen_files_sha256'][name], name
    package = b''.join(name.encode() + b'\0' + body for name, body in sorted(files.items()))
    assert hashlib.sha256(package).hexdigest() == provenance['frozen_package_sha256'], path.parent.name
    print(path.parent.name + ': frozen native package verified')
