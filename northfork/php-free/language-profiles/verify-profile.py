#!/usr/bin/env python3
"""Verify the persisted Node selection, offline package tools, and PHP absence."""
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
profile_id = sys.argv[1]
config = json.loads((root / 'profiles.json').read_text())
profile = config['profiles'][profile_id]
assert os.environ['NORTHFORK_LANGUAGE_PROFILE'] == profile_id
assert platform.machine() == {'amd64': 'x86_64', 'arm64': 'aarch64'}[profile['architecture']]

def output(command, **kwargs):
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT, **kwargs).strip()

version = profile['version']
assert output(['node', '--version']) == 'v' + version
cache = Path('/usr/local/n/versions/node') / version
assert hashlib.sha256(Path('/usr/local/bin/node').read_bytes()).digest() == hashlib.sha256((cache / 'bin/node').read_bytes()).digest()
npm_version = output(['npm', '--version'])
assert npm_version == json.loads((cache / 'lib/node_modules/npm/package.json').read_text())['version']
tools = {'node': version, 'npm': npm_version}
if 'yarn' in profile['package_tools']:
    tools['yarn'] = output(['yarn', '--version'])
    assert tools['yarn'] == config['package_tools']['yarn']['version']
if 'corepack' in profile['package_tools']:
    tools['corepack'] = output(['corepack', '--version'])
    assert tools['corepack'] == config['package_tools']['corepack']['version']
    tools['pnpm'] = output(['pnpm', '--version'], env={**os.environ, 'COREPACK_ENABLE_NETWORK': '0'})
    assert tools['pnpm'] == config['package_tools']['pnpm']['version']

with tempfile.TemporaryDirectory(prefix='node-profile-proof-') as folder:
    work = Path(folder)
    dependency = work / 'dependency'
    dependency.mkdir()
    (dependency / 'package.json').write_text(json.dumps({'name': 'local-profile-dependency', 'version': '1.0.0', 'main': 'index.js'}))
    (dependency / 'index.js').write_text('module.exports = {value: 7};\n')
    package = {'name': 'local-profile-proof', 'version': '1.0.0', 'private': True, 'scripts': {'proof': 'node proof.js'}, 'dependencies': {'local-profile-dependency': 'file:./dependency'}}
    (work / 'proof.js').write_text("const assert = require('assert'); assert.strictEqual(require('local-profile-dependency').value, 7); assert.strictEqual(process.version, 'v" + version + "'); console.log('OFFLINE_PROFILE_FIXTURE_PASSED');\n")
    commands = [(['npm', 'install', '--offline', '--ignore-scripts', '--no-audit', '--no-fund', '--package-lock=false'], ['npm', '--offline', 'run', 'proof'])]
    if 'yarn' in tools:
        commands.append((['yarn', 'install', '--offline', '--ignore-scripts', '--non-interactive', '--no-progress', '--no-lockfile'], ['yarn', '--offline', 'run', 'proof']))
    if 'pnpm' in tools:
        package['packageManager'] = 'pnpm@' + tools['pnpm']
        commands.append((['pnpm', 'install', '--offline', '--ignore-scripts', '--no-lockfile', '--store-dir', str(work / 'pnpm-store')], ['pnpm', 'run', 'proof']))
    (work / 'package.json').write_text(json.dumps(package))
    env = {**os.environ, 'COREPACK_ENABLE_NETWORK': '0', 'npm_config_cache': str(work / 'npm-cache'), 'YARN_CACHE_FOLDER': str(work / 'yarn-cache')}
    for install, proof in commands:
        subprocess.run(install, cwd=work, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        assert 'OFFLINE_PROFILE_FIXTURE_PASSED' in output(proof, cwd=work, env=env)

php_files = []
device = os.stat('/').st_dev
for directory, dirs, files in os.walk('/', topdown=True, followlinks=False):
    dirs[:] = [d for d in dirs if os.path.join(directory, d) not in ('/proc', '/sys', '/dev') and os.lstat(os.path.join(directory, d)).st_dev == device]
    for name in files:
        path = os.path.join(directory, name)
        if re.fullmatch(r'php(?:-cgi|-fpm|dbg)?[0-9.]*|php[0-9.]+(?:-cgi|-fpm)|libphp.*\.so(?:\..*)?', name) or ('.so' in name and re.search(r'/php[0-9.]*/(?:modules|extensions)(?:/|$)', path)):
            php_files.append(path)
packages = output(['rpm', '-qa', '--qf', '%{NAME}\n']).splitlines()
php_packages = [name for name in packages if re.match(r'^php(?:[0-9]*-|$)', name)]
assert not php_files and not php_packages, 'PHP remains in the language profile'
print('LANGUAGE_PROFILE_PROOF=' + json.dumps({'profile': profile_id, 'architecture': profile['architecture'], 'tools': tools, 'nodeBinarySha256': hashlib.sha256(Path('/usr/local/bin/node').read_bytes()).hexdigest(), 'cachedNodeBinaryMatchesSelected': True, 'offlinePackageFixturePassed': True, 'phpFiles': php_files, 'phpPackages': php_packages}))
