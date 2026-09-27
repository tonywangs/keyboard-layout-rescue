#!/usr/bin/env python3
"""One offline verification command, after documented browser prerequisites."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record',action='store_true',help='save actual test output to results/tests.log')
    args = parser.parse_args()
    commands = [
        [sys.executable,'scripts/xkb_oracle.py'],
        [sys.executable,'-m','unittest','discover','-s','tests','-v'],
        [sys.executable,'scripts/check_installed.py'],
        ['node','tests/browser.cjs'],
        [sys.executable,'scripts/check_comparison.py'],
        [sys.executable,'scripts/check_tree.py'],
    ]
    log = []
    for command in commands:
        heading = '$ '+' '.join(command)+'\n'
        print(heading,end='',flush=True)
        result = subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        print(result.stdout,end='',flush=True)
        log.extend([heading,result.stdout,f'Exit: {result.returncode}\n'])
        if result.returncode:
            if args.record: (ROOT/'results/tests.log').write_text(''.join(log))
            return result.returncode
    log.append('All verification stages passed. Benchmarks are separate: python3 scripts/benchmark.py\n')
    if args.record: (ROOT/'results/tests.log').write_text(''.join(log))
    print(log[-1],end='')
    return 0


if __name__=='__main__': raise SystemExit(main())
