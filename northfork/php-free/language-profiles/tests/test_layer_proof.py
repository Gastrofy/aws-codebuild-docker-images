import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'verify-image-layers.py'

class LayerProofTest(unittest.TestCase):
    def execute(self, file_name, corrupt_hash=False, reuse_base=False, wrong_base_id=False, wrong_prefix=False):
        layer = io.BytesIO()
        with tarfile.open(fileobj=layer, mode='w') as tar:
            data = b'fixture'
            member = tarfile.TarInfo(file_name)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
        digest = hashlib.sha256(layer.getvalue()).hexdigest()
        outer = io.BytesIO()
        with tarfile.open(fileobj=outer, mode='w') as tar:
            member = tarfile.TarInfo('blobs/sha256/' + digest)
            member.size = len(layer.getvalue())
            tar.addfile(member, io.BytesIO(layer.getvalue()))
        outer.seek(0)
        original = {'Config': {'Env': ['PATH=/usr/bin']}, 'Architecture': 'amd64', 'RootFS': {'Layers': []}, 'Id': 'sha256:base'}
        candidate = {'Config': {'Env': ['PATH=/usr/bin', 'NORTHFORK_LANGUAGE_PROFILE=node-18.20.8-amd64']}, 'Architecture': 'amd64', 'RootFS': {'Layers': ['sha256:' + ('a' * 64 if corrupt_hash else digest)]}, 'Id': 'sha256:fixture'}
        base_digest = 'sha256:' + 'b' * 64
        if reuse_base:
            original['RootFS']['Layers'] = [base_digest]
            candidate['RootFS']['Layers'].insert(0, 'sha256:' + 'c' * 64 if wrong_prefix else base_digest)
        class Process:
            stdout = outer
            def wait(self): return 0
            def kill(self): pass
        with tempfile.TemporaryDirectory() as folder:
            arguments = [str(SCRIPT), 'base', 'candidate', 'node-18.20.8-amd64']
            if reuse_base:
                proof = Path(folder) / 'base.json'
                proof.write_text(json.dumps({'image': 'base', 'image_id': 'sha256:wrong' if wrong_base_id else original['Id'], 'final_diff_ids': [base_digest], 'final_filesystem_layers_checked': 1, 'old_php_binary_or_module_in_any_final_layer': False, 'original_parent_diff_ids_retained': []}))
                arguments += ['--base-proof', str(proof)]
            with patch.object(sys, 'argv', arguments), patch('subprocess.check_output', side_effect=[json.dumps([original]), json.dumps([candidate])]), patch('subprocess.Popen', return_value=Process()), contextlib.redirect_stdout(io.StringIO()) as output:
                runpy.run_path(str(SCRIPT), run_name='__main__')
                return output.getvalue()

    def test_exact_layer_is_scanned(self):
        self.assertIn('noPhpRuntimeOrModuleInAnyLayer', self.execute('usr/bin/node'))

    def test_exact_verified_base_is_reused_and_new_layer_scanned(self):
        self.assertIn('"verifiedBaseLayersReused": 1', self.execute('usr/bin/node', reuse_base=True))

    def test_reuse_rejects_wrong_base_config(self):
        with self.assertRaises(AssertionError):
            self.execute('usr/bin/node', reuse_base=True, wrong_base_id=True)

    def test_reuse_rejects_wrong_parent_prefix(self):
        with self.assertRaises(AssertionError):
            self.execute('usr/bin/node', reuse_base=True, wrong_prefix=True)

    def test_reuse_still_rejects_php_in_new_layer(self):
        with self.assertRaises(AssertionError):
            self.execute('usr/bin/php', reuse_base=True)

    def test_php_in_a_distributed_layer_fails(self):
        with self.assertRaises(AssertionError):
            self.execute('usr/bin/php')

    def test_unmatched_layer_hash_fails(self):
        with self.assertRaises(AssertionError):
            self.execute('usr/bin/node', corrupt_hash=True)

if __name__ == '__main__':
    unittest.main()
