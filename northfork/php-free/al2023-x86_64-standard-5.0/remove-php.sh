#!/usr/bin/env bash
set -euo pipefail
# This image family compiles PHP under phpenv. Keep all other runtime managers.
rm -rf /root/.phpenv /root/.composer /usr/local/etc/php /usr/lib64/php /usr/lib/php
rm -f /usr/local/bin/composer /usr/bin/composer
# Remove packaged PHP only. Do not remove shared dependencies or unrelated tools.
mapfile -t php_packages < <(rpm -qa --qf '%{NAME}\n' | awk '/^php([0-9]*-|-|$)/')
if ((${#php_packages[@]})); then
    rpm -e "${php_packages[@]}"
fi
# An explicit php runtime selector must fail instead of reinstalling old versions.
python3 - <<'PY'
import re
from pathlib import Path
path = Path('/codebuild/image/config/runtimes.yml')
if path.exists():
    text = path.read_text()
    text = re.sub(r'(?ms)^  php:\n.*?(?=^  [A-Za-z0-9_-]+:|\Z)', '', text)
    assert not re.search(r'^  php:', text, re.M)
    path.write_text(text)
PY
# Reject any unaccounted runtime binary or shim. Do not silently delete unknown tools.
mapfile -t remaining < <(find / -xdev \( -type f -o -type l \) \( -name php -o -name php-cgi -o -name php-fpm -o -name phpdbg -o -name 'php[0-9]*' -o -name 'libphp*.so*' -o -name 'php-cgi[0-9]*' -o -name 'php-fpm[0-9]*' \) -print 2>/dev/null)
if ((${#remaining[@]})); then
    printf 'Unaccounted PHP runtime path: %s\n' "${remaining[@]}" >&2
    exit 1
fi
! command -v php
! command -v php-cgi
! command -v php-fpm
! command -v phpdbg
