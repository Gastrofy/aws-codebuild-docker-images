#!/usr/bin/env python3
"""Run reviewed local source commands with synthetic configuration and no deployment phase."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import parse_qsl, urlsplit


PACKAGE_CONFIG_NAMES = {'.npmrc', '.yarnrc', '.yarnrc.yml', '.yarnrc.yaml'}
CREDENTIAL_KEY = r'(?:_authToken|_auth|_password|password|username|npmAuthToken|npmAuthIdent|keyfile|certfile|httpsKeyFilePath|httpsCertFilePath)'
CREDENTIAL_CONFIG = re.compile(
    r'(?:^|[,{#;\s])[\"\']?(?://[^\s\"\'=]*:)?' + CREDENTIAL_KEY + r'[\"\']?\s*(?:[:=]|\s)',
    re.IGNORECASE,
)


def check_package_config(path):
    if path.name not in PACKAGE_CONFIG_NAMES or not path.is_file():
        return
    text = path.read_text(errors='replace')
    credential_url = False
    try:
        for url in re.findall(r'https?://[^\s\"\'<>]+', text):
            parsed = urlsplit(url)
            if parsed.username is not None or any(key.lower() in {'token', 'access_token', 'auth', 'auth_token', 'api_key', 'apikey', 'password', 'signature'}
                                                  for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
                credential_url = True
    except ValueError:
        raise ValueError('Invalid package manager registry URL') from None
    if CREDENTIAL_CONFIG.search(text) or credential_url:
        # Do not include a config value or its source line in an exception.
        raise ValueError('Credential-bearing package manager configuration is not allowed')


def redact_output(text, values):
    for value in sorted(values, key=len, reverse=True):
        text = text.replace(value, '[REDACTED]')
    text = re.sub(r'(' + CREDENTIAL_KEY + r'[\"\']?\s*[:=]\s*)(?:\"[^\"\n]*\"|\'[^\'\n]*\'|[^\s,;]+)',
                  r'\1[REDACTED]', text, flags=re.IGNORECASE)
    return re.sub(r'https?://[^\s\"\'<>]+', '[URL_REDACTED]', text)


def source_tree(root):
    files = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if '.git' in path.relative_to(root).parts:
            continue
        if path.is_symlink():
            target = os.readlink(path)
            assert not os.path.isabs(target)
            assert path.resolve().is_relative_to(root.resolve()), relative
            data = target.encode()
        elif path.is_file():
            data = path.read_bytes()
        else:
            continue
        files.append([relative, hashlib.sha256(data).hexdigest()])
    return hashlib.sha256(json.dumps(files, separators=(',', ':')).encode()).hexdigest(), len(files)


def prepare_workspace(source, target):
    excluded = []
    for path in source.rglob('*'):
        relative = path.relative_to(source)
        if any(part == '.git' or part == 'node_modules' or part.startswith('.env') for part in relative.parts):
            if path.is_file():
                excluded.append(relative.as_posix())
            continue
        check_package_config(path)
        destination = target / relative
        if path.is_symlink():
            assert path.resolve().is_relative_to(source.resolve())
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(os.readlink(path))
        elif path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    return excluded


def clean_environment(home, fixtures):
    # Keep only tool lookup and locale. Never inherit CodeBuild credentials or application values.
    result = {'PATH': os.environ['PATH'], 'HOME': str(home), 'LANG': 'en_US.utf8', 'LC_ALL': 'en_US.utf8',
              'CI': 'true', 'NEXT_TELEMETRY_DISABLED': '1', 'SST_TELEMETRY_DISABLED': '1',
              'AWS_EC2_METADATA_DISABLED': 'true', 'AWS_ACCESS_KEY_ID': 'qualification-only',
              'AWS_SECRET_ACCESS_KEY': 'qualification-only', 'AWS_DEFAULT_REGION': 'eu-central-1',
              'AWS_REGION': 'eu-central-1', 'npm_config_cache': str(home / 'npm-cache'),
              'YARN_CACHE_FOLDER': str(home / 'yarn-cache'), 'COREPACK_HOME': '/root/.cache/node/corepack'}
    assert not any(k.startswith(('CODEBUILD_', 'AWS_CONTAINER_', 'AWS_SESSION_')) for k in fixtures)
    assert not any(k in fixtures for k in ['PATH', 'HOME', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'])
    result.update(fixtures)
    return result



def dependency_hooks(root):
    """Record installed package hooks without executing them."""
    hooks = []
    for path in sorted((root / 'node_modules').rglob('package.json')):
        if path.is_symlink() or not path.is_file():
            continue
        package = json.loads(path.read_text())
        scripts = {key: value for key, value in package.get('scripts', {}).items()
                   if key in ['preinstall', 'install', 'postinstall', 'prepare']}
        if scripts:
            hooks.append({'path': path.relative_to(root).as_posix(), 'name': package.get('name'),
                          'version': package.get('version'), 'scripts': scripts,
                          'manifestSha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return hooks


def run(contract):
    source = Path(os.environ['CODEBUILD_SRC_DIR']).resolve()
    tree, count = source_tree(source)
    assert tree == contract['sourceTreeSha256'] and count == contract['sourceFileCount']
    assert platform.machine() == {'amd64': 'x86_64', 'arm64': 'aarch64'}[contract['architecture']]
    assert subprocess.check_output(['node', '--version'], text=True).strip() == 'v' + contract['node']
    assert shutil.which('php') is None and shutil.which('php-fpm') is None
    redactions = {value for value in os.environ.values() if len(value) >= 8}
    for path in source.rglob('.env*'):
        if path.is_file():
            for line in path.read_text(errors='replace').splitlines():
                if '=' in line:
                    value = line.split('=', 1)[1].strip().strip('\"\'')
                    if len(value) >= 4:
                        redactions.add(value)
    with tempfile.TemporaryDirectory(prefix='source-qualification-') as folder:
        root = Path(folder)
        work, home = root / 'source', root / 'home'
        work.mkdir(); home.mkdir()
        excluded = prepare_workspace(source, work)
        env = clean_environment(home, contract['syntheticEnvironment'])
        (work / '.env').write_text(''.join(k + '=' + value + '\n' for k, value in contract['syntheticEnvironment'].items()))
        records = []
        for index, command in enumerate(contract['commands']):
            # Commands are review-bound argv arrays. There is no original buildspec or shell evaluation.
            assert isinstance(command, list) and all(isinstance(arg, str) for arg in command)
            result = subprocess.run(command, cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1200)
            log = root / ('command-' + str(index) + '.log')
            log.write_bytes(result.stdout); log.chmod(0o600)
            record = {'command': command, 'exitCode': result.returncode, 'outputSha256': hashlib.sha256(result.stdout).hexdigest()}
            records.append(record)
            print('NODE_SOURCE_COMMAND=' + json.dumps(record), flush=True)
            if result.returncode == 0 and command[0] in ['npm', 'yarn', 'pnpm'] and any(arg in ['install', 'ci'] for arg in command[1:]) and not '-g' in command:
                print('NODE_DEPENDENCY_HOOKS=' + json.dumps({'commandIndex': index, 'packages': dependency_hooks(work)}), flush=True)
            if result.returncode:
                text = redact_output(result.stdout.decode(errors='replace'), redactions)
                print('NODE_SOURCE_FAILURE=' + json.dumps({'commandIndex': index, 'tail': text.splitlines()[-35:]}), flush=True)
                raise RuntimeError('The reviewed source command failed')
        for required in contract['expectedOutputs']:
            assert (work / required).exists(), required
        proof = {'id': contract['id'], 'project': contract['project'], 'sourceTreeSha256': tree, 'sourceFileCount': count,
                 'architecture': contract['architecture'], 'node': contract['node'], 'sourceArtifactSha256': contract['sourceArtifactSha256'],
                 'commands': records, 'syntheticEnvironmentKeys': sorted(contract['syntheticEnvironment']),
                 'productionEnvironmentFilesExcluded': len(excluded), 'productionCredentialsPassed': False,
                 'originalDeployAndPostBuildExecuted': False, 'expectedOutputsVerified': contract['expectedOutputs']}
        print('NODE_SOURCE_QUALIFICATION_PROOF=' + json.dumps(proof), flush=True)


if __name__ == '__main__':
    run(json.loads(Path(sys.argv[1]).read_text()))
