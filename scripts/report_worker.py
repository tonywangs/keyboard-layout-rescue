#!/usr/bin/env python3
"""Fresh-process renderer used only by the paired experiment."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))
from report_workloads import CASES
from keyboard_rescue.cli import atomic_export

if __name__ == '__main__':
    variant, case, destination = sys.argv[1:]
    if variant == 'baseline':
        from baseline.core import analyze
        from baseline.report import html_text
    elif variant == 'candidate':
        from keyboard_rescue.core import analyze
        from keyboard_rescue.report import html_text
    else:
        raise ValueError(variant)
    text, geometry = CASES[case]
    report = analyze(text,'qwerty',['colemak','dvorak'],geometry)
    atomic_export(Path(destination),html_text(report).encode())
