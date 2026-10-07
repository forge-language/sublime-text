#!/usr/bin/env python3
"""Build the installable package from an explicit, reproducible file list."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    '.python-version', 'LICENSE', 'README.md', 'LSP-Forge.py',
    'LSP-Forge.sublime-settings', 'Forge.sublime-syntax',
    'Forge.sublime-settings', 'Forge.sublime-build',
    'Comments.tmPreferences',
    'Main.sublime-menu', 'Default.sublime-commands',
]


def build():
    files = FILES + sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'snippets').glob('*.sublime-snippet'))
    target = ROOT / 'dist' / 'LSP-Forge.sublime-package'
    target.parent.mkdir(exist_ok=True)
    temporary = target.with_suffix('.tmp')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name in sorted(files):
            source = ROOT / name
            if source.is_symlink() or not source.is_file():
                raise ValueError('Missing or unsafe package resource: ' + name)
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            package.writestr(entry, source.read_bytes())
    temporary.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_name(target.name + '.sha256').write_text(digest + '  ' + target.name + '\n')
    print(str(target))
    print(digest)
    return target


if __name__ == '__main__':
    build()
