import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import sys
import tarfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'verify-image-layers.py'

class LayerProofTest(unittest.TestCase):
    def execute(self, file_name, corrupt_hash=False):
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
        class Process:
            stdout = outer
            def wait(self): return 0
            def kill(self): pass
        with patch.object(sys, 'argv', [str(SCRIPT), 'base', 'candidate', 'node-18.20.8-amd64']), patch('subprocess.check_output', side_effect=[json.dumps([original]), json.dumps([candidate])]), patch('subprocess.Popen', return_value=Process()), contextlib.redirect_stdout(io.StringIO()) as output:
            runpy.run_path(str(SCRIPT), run_name='__main__')
            return output.getvalue()

    def test_exact_layer_is_scanned(self):
        self.assertIn('noPhpRuntimeOrModuleInAnyLayer', self.execute('usr/bin/node'))

    def test_php_in_a_distributed_layer_fails(self):
        with self.assertRaises(AssertionError):
            self.execute('usr/bin/php')

    def test_unmatched_layer_hash_fails(self):
        with self.assertRaises(AssertionError):
            self.execute('usr/bin/node', corrupt_hash=True)

if __name__ == '__main__':
    unittest.main()
