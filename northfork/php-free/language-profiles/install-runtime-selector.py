#!/usr/bin/env python3
"""Add only the missing legacy Node selector to the official runtime catalog."""
from pathlib import Path
import sys
import yaml


def add_selector(catalog, version):
    major = int(version.split('.')[0])
    assert major in (12, 16)
    assert 'php' not in catalog['runtimes']
    versions = catalog['runtimes']['nodejs']['versions']
    assert major not in versions and str(major) not in versions
    versions[major] = {'commands': ['n --offline --no-preserve ' + version, 'test "$(node --version)" = "v' + version + '"']}
    return catalog


if __name__ == '__main__':
    path = Path('/codebuild/image/config/runtimes.yml')
    catalog = add_selector(yaml.safe_load(path.read_text()), sys.argv[1])
    path.write_text(yaml.safe_dump(catalog, sort_keys=False))
