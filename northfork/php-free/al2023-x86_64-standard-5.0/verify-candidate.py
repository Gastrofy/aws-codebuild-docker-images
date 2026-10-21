import fnmatch
import json
import re
import subprocess
import tarfile
from pathlib import Path

base = json.loads(Path('base-config.json').read_text())
image = 'ci-builder-proof:validated'
def inspect(ref):
    return json.loads(subprocess.check_output(['docker', 'image', 'inspect', ref]))[0]
config = inspect(image)
expected = {}
for item in base['config']['Env']:
    key, value = item.split('=', 1)
    if key.startswith('PHP') or key in ('PHPRC', 'PHPENV_ROOT'):
        continue
    if key == 'PATH':
        value = ':'.join(p for p in value.split(':') if '.phpenv' not in p)
    expected[key] = value
actual = dict(item.split('=', 1) for item in config['Config']['Env'])
assert actual == expected, 'Candidate ENV does not exactly preserve non-PHP values'
for key in ('Entrypoint', 'WorkingDir', 'Volumes'):
    assert config['Config'].get(key) == base['config'].get(key), key
original_diff_ids = set(base['rootfs']['diff_ids'])
final_diff_ids = config['RootFS']['Layers']
intersection = sorted(original_diff_ids.intersection(final_diff_ids))
recipe = Path('Dockerfile').read_text()
assert [line.strip() for line in recipe.splitlines() if line.startswith('FROM ')][-1] == 'FROM scratch'
assert 'COPY --from=sanitized / /' in recipe
history = subprocess.check_output(['docker', 'history', '--no-trunc', '--format', '{{.CreatedBy}}', image], text=True).splitlines()
diagnostics = {'original_layer_count': len(original_diff_ids), 'final_diff_ids': final_diff_ids, 'original_diff_ids_retained': intersection, 'final_history_instruction_types': [line.split()[0] if line.split() else 'empty' for line in history], 'recipe_final_from_scratch': True}
print('CI_BUILDER_LAYER_DIAGNOSTICS=' + json.dumps(diagnostics), flush=True)
assert not intersection, 'Candidate retains original parent layer diffIDs'
assert all(line.startswith(('ENV ', 'WORKDIR ', 'COPY ', 'VOLUME ', 'ENTRYPOINT ', 'CMD ')) or line.startswith('/bin/sh -c #(nop)') for line in history), 'Unexpected final-stage history'
subprocess.run(['docker', 'save', '-o', '/tmp/candidate-image.tar', image], check=True)
checked_layers = 0
with tarfile.open('/tmp/candidate-image.tar') as archive:
    manifest = json.load(archive.extractfile('manifest.json'))[0]
    assert len(manifest['Layers']) == len(final_diff_ids)
    saved_config = json.load(archive.extractfile(manifest['Config']))
    assert saved_config['rootfs']['diff_ids'] == final_diff_ids
    for layer in manifest['Layers']:
        with tarfile.open(fileobj=archive.extractfile(layer)) as filesystem:
            for entry in filesystem:
                name = entry.name.lstrip('./')
                leaf = name.rsplit('/', 1)[-1]
                assert not name.startswith('root/.phpenv/'), 'Old PHP installation remains in final layer'
                if entry.isfile() or entry.issym() or entry.islnk():
                    assert not any(fnmatch.fnmatch(leaf, pattern) for pattern in ('php', 'php-cgi', 'php-fpm', 'phpdbg', 'php[0-9]*', 'libphp*.so*')), 'PHP runtime or module remains in final layer: ' + name
                    assert not ('.so' in leaf and re.search(r'(?:^|/)php[0-9.]*/(?:modules|extensions)(?:/|$)', name)), 'PHP extension module remains in final layer: ' + name
        checked_layers += 1
Path('/tmp/candidate-image.tar').unlink()
proof = {'environment_preserved_exactly': True, 'environment_keys': len(expected), 'escaped_newline_value_preserved': actual['GRADLE_DOWNLOADS_SHA256'] == expected['GRADLE_DOWNLOADS_SHA256'], 'entrypoint_workdir_volumes_preserved': True, 'final_filesystem_layers_checked': checked_layers, 'original_parent_diff_ids_retained': intersection, 'final_diff_ids': final_diff_ids, 'recipe_final_from_scratch': True, 'old_php_binary_or_module_in_any_final_layer': False, 'image_id': config['Id'], 'architecture': config['Architecture']}
Path('filesystem-proof.json').write_text(json.dumps(proof, indent=2))
print('CI_BUILDER_FILESYSTEM_PROOF=' + json.dumps(proof))
