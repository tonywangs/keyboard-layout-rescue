#!/usr/bin/env python3
"""Install into a NEW isolated environment, offline and without pip (POSIX)."""
import argparse
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def install(prefix):
    prefix = Path(prefix).absolute()
    # mkdir is exclusive, including existing symlinks. Never clean up an existing environment.
    prefix.mkdir(mode=0o700)
    try:
        venv.EnvBuilder(with_pip=False).create(prefix)
        python = prefix / 'bin/python'
        site = Path(subprocess.check_output([str(python), '-I', '-c',
                    'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True).strip())
        package = site / 'keyboard_rescue'
        package.mkdir()
        for source in (ROOT / 'keyboard_rescue').iterdir():
            if source.suffix in ('.py', '.html') or source.name == 'XKB-COPYING':
                shutil.copyfile(source, package / source.name)
        launcher = prefix / 'bin/keyboard-rescue'
        launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(str(python)) + ' -I -m keyboard_rescue "$@"\n')
        launcher.chmod(0o755)
        print(launcher)
    except BaseException:
        shutil.rmtree(prefix)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', help='new environment directory; parent must exist')
    args = parser.parse_args()
    if sys.platform == 'win32':
        parser.error('offline installer requires POSIX; use pip on Windows (file export is not validated there)')
    try:
        install(args.prefix)
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f'install: {error}\n')
