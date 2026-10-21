import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('qualify', Path(__file__).resolve().parents[1] / 'qualify.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceContractTest(unittest.TestCase):
    def test_content_hash_changes_when_source_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder); (path / 'app.js').write_text('a')
            first, count = module.source_tree(path)
            (path / 'app.js').write_text('b')
            self.assertEqual(count, 1)
            self.assertNotEqual(first, module.source_tree(path)[0])

    def test_workspace_preserves_business_bytes_and_excludes_environment_files(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source', Path(folder) / 'target'
            source.mkdir(); target.mkdir()
            (source / 'app.js').write_bytes(b'original bytes')
            (source / '.env.production').write_text('SECRET=real-value')
            excluded = module.prepare_workspace(source, target)
            self.assertEqual((target / 'app.js').read_bytes(), b'original bytes')
            self.assertFalse((target / '.env.production').exists())
            self.assertEqual(excluded, ['.env.production'])

    def test_credentials_and_metadata_do_not_enter_application_environment(self):
        with patch.dict(os.environ, {'PATH': '/usr/bin', 'AWS_SESSION_TOKEN': 'real-token', 'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI': '/secret', 'DATABASE_PASSWORD': 'real-password'}, clear=True):
            clean = module.clean_environment(Path('/tmp/proof'), {'VITE_CC_API_URL': 'https://example.invalid'})
            self.assertNotIn('AWS_SESSION_TOKEN', clean)
            self.assertNotIn('AWS_CONTAINER_CREDENTIALS_RELATIVE_URI', clean)
            self.assertNotIn('DATABASE_PASSWORD', clean)
            self.assertEqual(clean['AWS_SECRET_ACCESS_KEY'], 'qualification-only')

    def test_dependency_hooks_are_recorded_without_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = root / 'node_modules' / 'example' / 'package.json'
            package.parent.mkdir(parents=True)
            package.write_text(json.dumps({'name': 'example', 'version': '1.2.3',
                                           'scripts': {'install': 'touch NEVER_RUN', 'test': 'ignored'}}))
            hooks = module.dependency_hooks(root)
            self.assertEqual(hooks[0]['scripts'], {'install': 'touch NEVER_RUN'})
            self.assertEqual(hooks[0]['version'], '1.2.3')
            self.assertFalse((root / 'NEVER_RUN').exists())

    def test_external_symlink_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'external').symlink_to('/etc/passwd')
            with self.assertRaises(AssertionError):
                module.source_tree(root)


if __name__ == '__main__':
    unittest.main()
