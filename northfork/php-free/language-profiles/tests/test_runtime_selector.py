import copy
from pathlib import Path
import runpy
import unittest

ADD = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'install-runtime-selector.py'))['add_selector']


class RuntimeSelectorTest(unittest.TestCase):
    def test_legacy_selector_preserves_existing_catalog(self):
        original = {'version': 0.1, 'runtimes': {'nodejs': {'versions': {20: {'commands': ['n $NODE_20_VERSION']}}}, 'python': {'versions': {3.11: {'commands': ['pyenv global 3.11']}}}}}
        updated = ADD(copy.deepcopy(original), '16.20.2')
        self.assertEqual(updated['runtimes']['nodejs']['versions'].pop(16), {'commands': ['n --offline --no-preserve 16.20.2', 'test "$(node --version)" = "v16.20.2"']})
        self.assertEqual(updated, original)

    def test_existing_selector_is_not_overwritten(self):
        with self.assertRaises(AssertionError):
            ADD({'runtimes': {'nodejs': {'versions': {12: {}}}}}, '12.22.12')

    def test_php_catalog_fails_closed(self):
        with self.assertRaises(AssertionError):
            ADD({'runtimes': {'php': {}, 'nodejs': {'versions': {}}}}, '12.22.12')


if __name__ == '__main__':
    unittest.main()
