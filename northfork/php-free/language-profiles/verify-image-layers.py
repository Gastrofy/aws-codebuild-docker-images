#!/usr/bin/env python3
"""Stream every distributed layer and bind profile invariants to the native base."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import re
import subprocess
import sys
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument('base')
parser.add_argument('image')
parser.add_argument('profile')
parser.add_argument('--base-proof')
args = parser.parse_args()
base, image, profile_id = args.base, args.image, args.profile
def inspect(ref):
    return json.loads(subprocess.check_output(['docker', 'image', 'inspect', ref], text=True))[0]
original, candidate = inspect(base), inspect(image)
expected = dict(value.split('=', 1) for value in original['Config']['Env'])
expected['NORTHFORK_LANGUAGE_PROFILE'] = profile_id
if profile_id.startswith('node-24.19.0-'):
    expected['COREPACK_ENABLE_NETWORK'] = '0'
assert dict(value.split('=', 1) for value in candidate['Config']['Env']) == expected
for field in ['Entrypoint', 'Cmd', 'WorkingDir', 'User', 'Volumes']:
    assert candidate['Config'].get(field) == original['Config'].get(field), field
assert candidate['Architecture'] == original['Architecture']
expected_layers = candidate['RootFS']['Layers']
base_layers = original['RootFS']['Layers']
assert expected_layers[:len(base_layers)] == base_layers, 'The exact verified base must be the layer prefix'
reused_layers = []
if args.base_proof:
    with open(args.base_proof) as source:
        proof = json.load(source)
    assert proof['image'] == base and proof['image_id'] == original['Id']
    assert proof['final_diff_ids'] == base_layers
    assert proof['final_filesystem_layers_checked'] == len(base_layers)
    assert proof['old_php_binary_or_module_in_any_final_layer'] is False
    assert not proof['original_parent_diff_ids_retained']
    reused_layers = base_layers
new_layers = expected_layers[len(reused_layers):]
blob_names = {value.split(':', 1)[1] for value in expected_layers}
reused_blob_names = {value.split(':', 1)[1] for value in reused_layers}
observed = []

class HashedReader:
    def __init__(self, stream):
        self.stream, self.hash = stream, hashlib.sha256()
    def read(self, size=-1):
        data = self.stream.read(size)
        self.hash.update(data)
        return data

process = subprocess.Popen(['docker', 'image', 'save', image], stdout=subprocess.PIPE)
try:
    with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
        for member in archive:
            if not member.isfile():
                continue
            name = member.name.lstrip('./')
            if PurePosixPath(name).name in reused_blob_names:
                continue
            if reused_layers:
                assert not name.endswith('/layer.tar'), 'Digest-addressed archive paths are required for verified base reuse'
            if not (name.endswith('/layer.tar') or PurePosixPath(name).name in blob_names):
                continue
            stream = HashedReader(archive.extractfile(member))
            with tarfile.open(fileobj=stream, mode='r|') as layer:
                for entry in layer:
                    path = entry.name.lstrip('./')
                    leaf = PurePosixPath(path).name
                    assert not path.startswith('root/.phpenv/'), path
                    if entry.isfile() or entry.issym() or entry.islnk():
                        assert not re.fullmatch(r'php(?:-cgi|-fpm|dbg)?[0-9.]*|php[0-9.]+(?:-cgi|-fpm)|libphp.*\.so(?:\..*)?', leaf), path
                        assert not ('.so' in leaf and re.search(r'(?:^|/)php[0-9.]*/(?:modules|extensions)(?:/|$)', path)), path
            while stream.read(1024 * 1024):
                pass
            observed.append('sha256:' + stream.hash.hexdigest())
    assert process.wait() == 0
except BaseException:
    process.kill()
    process.wait()
    raise
assert Counter(observed) == Counter(new_layers), 'Every exact new filesystem layer must be scanned'
print('LANGUAGE_PROFILE_LAYER_PROOF=' + json.dumps({'profile': profile_id, 'base': base, 'imageId': candidate['Id'], 'architecture': candidate['Architecture'], 'entrypointCmdWorkdirUserVolumesPreserved': True, 'unrelatedEnvironmentPreserved': True, 'layersChecked': len(observed), 'verifiedBaseLayersReused': len(reused_layers), 'verifiedBaseConfigDigest': original['Id'], 'exactParentLayerPrefixVerified': True, 'newLayerDiffIdsChecked': new_layers, 'layerDiffIds': expected_layers, 'noPhpRuntimeOrModuleInAnyLayer': True}))
