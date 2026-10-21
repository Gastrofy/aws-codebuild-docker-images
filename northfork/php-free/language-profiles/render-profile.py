#!/usr/bin/env python3
"""Render a profile Dockerfile. This command never builds, pushes, or deploys."""
import argparse
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('profile')
parser.add_argument('--base', required=True)
args = parser.parse_args()
assert re.fullmatch(r'[a-zA-Z0-9./_-]+@sha256:[a-f0-9]{64}', args.base), 'Use the verified PHP-free native base digest'
profile = json.loads((root / 'profiles.json').read_text())['profiles'][args.profile]
lines = ['FROM ' + args.base, 'COPY . /opt/northfork/language-profile', 'ENV NORTHFORK_LANGUAGE_PROFILE=' + args.profile]
if profile['language'] == 'node':
    lines += ['RUN bash /opt/northfork/language-profile/install-node.sh ' + ' '.join([profile['version'], profile['architecture'], profile.get('archive_sha256', 'cached')]), 'RUN python3 /opt/northfork/language-profile/install-package-tools.py ' + args.profile]
    if 'corepack' in profile.get('package_tools', []):
        lines += ['ENV COREPACK_ENABLE_NETWORK=0']
else:
    raise ValueError('Only retained Node profiles are approved; resolver-java awaits retirement review')
lines += ['RUN python3 /opt/northfork/language-profile/verify-profile.py ' + args.profile]
print('\n'.join(lines))
