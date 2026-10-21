import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ProfileContractTest(unittest.TestCase):
    def test_profiles_cover_only_retained_architectures_and_versions(self):
        config = json.loads((ROOT / 'profiles.json').read_text())
        actual = {(p['architecture'], p['version']) for p in config['profiles'].values()}
        self.assertEqual(actual, {('amd64', '12.22.12'), ('amd64', '16.20.2'), ('amd64', '18.20.8'), ('amd64', '20.20.2'), ('amd64', '22.23.3'), ('amd64', '24.19.0'), ('arm64', '20.20.2')})
        self.assertEqual(sum(len(p['projects']) for p in config['profiles'].values()), 11)
        for p in config['profiles'].values():
            self.assertNotIn('resolver-java', p['projects'])

    def test_renderer_requires_immutable_base_and_preserves_exact_selection(self):
        renderer = [sys.executable, str(ROOT / 'render-profile.py'), 'node-24.19.0-amd64']
        result = subprocess.run(renderer + ['--base', 'example/builder:latest'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        digest = 'example/builder@sha256:' + 'a' * 64
        text = subprocess.check_output(renderer + ['--base', digest], text=True)
        self.assertIn('FROM ' + digest, text)
        self.assertIn('24.19.0 amd64 14b342e71204f811bde6153be8e04b62aef63c236fef92b55f9c83154b409647', text)
        self.assertIn('ENV COREPACK_ENABLE_NETWORK=0', text)
        self.assertNotIn('ENTRYPOINT', text)
        self.assertNotIn('WORKDIR', text)
        self.assertNotIn('latest', text)

if __name__ == '__main__':
    unittest.main()
