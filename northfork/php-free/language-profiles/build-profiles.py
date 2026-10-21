#!/usr/bin/env python3
"""Build and verify reviewed native profiles. Publication requires an explicit flag."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--base', required=True)
parser.add_argument('--publish', action='store_true')
parser.add_argument('--base-proof')
parser.add_argument('profiles', nargs='+')
args = parser.parse_args()
assert re.fullmatch(r'950664063715\.dkr\.ecr\.eu-central-1\.amazonaws\.com/northfork/php-security-base@sha256:[a-f0-9]{64}', args.base)
config = json.loads((root / 'profiles.json').read_text())
recipe_files = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in root.rglob('*') if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'}
context_sha = hashlib.sha256(json.dumps(recipe_files, sort_keys=True).encode()).hexdigest()
for name in args.profiles:
    assert config['profiles'][name]['architecture'] == {'x86_64': 'amd64', 'aarch64': 'arm64'}[platform.machine()]

def output(command, **kwargs):
    return subprocess.check_output(command, text=True, **kwargs).strip()

def record(command, prefix):
    text = output(command)
    print(text, flush=True)
    return json.loads(next(line.split('=', 1)[1] for line in text.splitlines() if line.startswith(prefix + '=')))

repository = '950664063715.dkr.ecr.eu-central-1.amazonaws.com/northfork/php-security-base'
password = subprocess.check_output(['aws', 'ecr', 'get-login-password', '--region', 'eu-central-1'])
subprocess.run(['docker', 'login', '--username', 'AWS', '--password-stdin', repository.split('/')[0]], input=password, check=True)
subprocess.run(['docker', 'pull', args.base], check=True)
if args.publish:
    assert os.environ['CODEBUILD_BUILD_NUMBER'].isdigit()
for name in args.profiles:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.Dockerfile') as dockerfile:
        text = output([sys.executable, str(root / 'render-profile.py'), name, '--base', args.base])
        dockerfile.write(text)
        dockerfile.flush()
        recipe_sha = hashlib.sha256(text.encode()).hexdigest()
        image = 'northfork-language-profile:' + name
        subprocess.run(['docker', 'build', '--platform', 'linux/' + config['profiles'][name]['architecture'], '-f', dockerfile.name, '-t', image, str(root)], check=True)
    runtime = record(['docker', 'run', '--rm', '--network=none', '--read-only', '--tmpfs', '/tmp', '--entrypoint', 'python3', image, '/opt/northfork/language-profile/verify-profile.py', name], 'LANGUAGE_PROFILE_PROOF')
    layer_command = [sys.executable, str(root / 'verify-image-layers.py'), args.base, image, name]
    if args.base_proof:
        layer_command += ['--base-proof', args.base_proof]
    layers = record(layer_command, 'LANGUAGE_PROFILE_LAYER_PROOF')
    proof = {'profile': name, 'base': args.base, 'renderedRecipeSha256': recipe_sha, 'recipeContextSha256': context_sha, 'recipeFileSha256': recipe_files, 'imageId': layers['imageId'], 'runtime': runtime, 'layers': layers, 'published': False}
    if args.publish:
        tag = 'ci-' + name + '-' + context_sha[:12] + '-' + os.environ['CODEBUILD_BUILD_NUMBER']
        reference = repository + ':' + tag
        subprocess.run(['docker', 'tag', image, reference], check=True)
        subprocess.run(['docker', 'push', reference], check=True)
        digest = output(['aws', 'ecr', 'describe-images', '--region', 'eu-central-1', '--repository-name', 'northfork/php-security-base', '--image-ids', 'imageTag=' + tag, '--query', 'imageDetails[0].imageDigest', '--output', 'text'])
        assert re.fullmatch(r'sha256:[a-f0-9]{64}', digest)
        immutable = repository + '@' + digest
        subprocess.run(['docker', 'pull', immutable], check=True)
        assert output(['docker', 'image', 'inspect', immutable, '--format', '{{.Id}}']) == layers['imageId']
        proof.update({'published': True, 'image': immutable, 'tag': tag, 'publishedConfigMatchesTested': True})
    print('LANGUAGE_PROFILE_BUILD_PROOF=' + json.dumps(proof), flush=True)
