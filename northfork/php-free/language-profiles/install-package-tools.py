#!/usr/bin/env python3
"""Install checksum-pinned standalone package tools. No npm lifecycle scripts run."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

root = Path(__file__).resolve().parent
profile = json.loads((root / 'profiles.json').read_text())['profiles'][sys.argv[1]]
packages = json.loads((root / 'profiles.json').read_text())['package_tools']
for name in profile.get('package_tools', []):
    package = packages[name]
    with urllib.request.urlopen(package['url'], timeout=60) as response:
        data = response.read()
    algorithm, expected = package['integrity'].split('-', 1)
    assert base64.b64encode(hashlib.new(algorithm, data).digest()).decode() == expected
    target = Path('/opt/northfork') / (name + '-' + package['version'])
    target.mkdir(parents=True, exist_ok=False)
    with tempfile.NamedTemporaryFile(suffix='.tgz') as archive:
        archive.write(data)
        archive.flush()
        with tarfile.open(archive.name) as source:
            source.extractall(target, filter='data')
    for command, relative in package['bin'].items():
        destination = Path('/usr/local/bin') / command
        if destination.is_symlink() or destination.exists():
            destination.unlink()
        destination.symlink_to(target / 'package' / relative)
    assert subprocess.check_output([name, '--version'], text=True).strip() == package['version']
if 'corepack' in profile.get('package_tools', []):
    package = packages['pnpm']
    digest = base64.b64decode(package['integrity'].split('-', 1)[1]).hex()
    subprocess.run(['corepack', 'enable'], check=True)
    subprocess.run(['corepack', 'install', '--global', 'pnpm@' + package['version'] + '+sha512.' + digest], check=True)
    assert subprocess.check_output(['pnpm', '--version'], text=True, env={**os.environ, 'COREPACK_ENABLE_NETWORK': '0'}).strip() == package['version']
