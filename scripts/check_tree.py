#!/usr/bin/env python3
"""Check publishable tracked + nonignored project files against artifact limits."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def check():
    result = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT)
    names = sorted(set(x.decode() for x in result.split(b'\0') if x))
    total = 0
    for name in names:
        path = ROOT/name
        assert path.is_file() and not path.is_symlink(), f'not a regular file: {name}'
        size = path.stat().st_size
        assert size <= 10*1024*1024, f'file exceeds 10 MiB: {name}'
        assert not name.endswith('.log') or name=='results/tests.log', f'non-test log: {name}'
        assert not any(part in {'.git','.agents','.codex','node_modules','.venv','__pycache__'} for part in path.relative_to(ROOT).parts),name
        total += size
    assert len(names)<=1000, f'{len(names)} files exceeds 1000'
    assert total<=32*1024*1024, f'{total} bytes exceeds 32 MiB'
    print(f'Publication limits: {len(names)} regular files, {total} bytes; every file <= 10 MiB.')


if __name__=='__main__': check()
