#!/usr/bin/env python3
"""Six balanced paired observations on frozen workloads; Linux, no generated artifacts retained."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from report_workloads import CASES, manifest


def run(repetitions):
    assert manifest() == json.loads((ROOT/'tests/workloads.json').read_text())
    observations = []
    hashes = {}
    with tempfile.TemporaryDirectory(prefix='rescue-paired-') as folder:
        output = Path(folder)/'report.html'
        for repetition in range(repetitions):
            # AB / BA alternates within each workload; rotate cases to spread drift.
            names = list(CASES)
            names = names[repetition % len(names):]+names[:repetition % len(names)]
            for case in names:
                order = ['baseline','candidate'] if repetition % 2 == 0 else ['candidate','baseline']
                for variant in order:
                    measured = json.loads(subprocess.check_output([
                        sys.executable,str(ROOT/'scripts/measure_process.py'),sys.executable,
                        str(ROOT/'scripts/report_worker.py'),variant,case,str(output)],cwd=ROOT,text=True))
                    assert measured['returncode'] == 0, measured
                    size = output.stat().st_size
                    digest = hashlib.sha256(output.read_bytes()).hexdigest()
                    assert hashes.setdefault((case,variant),digest)==digest,'nondeterministic report'
                    if variant=='candidate': assert size < 10*1024*1024
                    browser = json.loads(subprocess.check_output(['node','scripts/measure_browser.cjs',str(output)],cwd=ROOT,text=True))
                    observations.append({'repetition':repetition+1,'case':case,'variant':variant,'pair_order':order,
                                         'artifact_bytes':size,'artifact_sha256':digest,'generation':measured,'browser':browser})
                    output.unlink()
                    print(f'{repetition+1}/{repetitions} {case} {variant}: {size} bytes',file=sys.stderr,flush=True)
    summaries = {}
    for case in CASES:
        summaries[case] = {}
        for variant in ('baseline','candidate'):
            rows = [r for r in observations if r['case']==case and r['variant']==variant]
            summaries[case][variant] = {'artifact_bytes':rows[0]['artifact_bytes'],
                'median_generation_seconds':statistics.median(r['generation']['wall_seconds'] for r in rows),
                'median_peak_rss_kib':statistics.median(r['generation']['peak_rss_kib'] for r in rows),
                **{'median_'+key:statistics.median(values) if (values := [r['browser'][key] for r in rows if r['browser'][key] is not None]) else None
                   for key in ('load_ms','select_ms','switch_ms','text_next_ms','diagnostic_next_ms','filter_ms')},
                'selected_dom':rows[0]['browser']['selected_dom']}
    return {'schema':1,'repetitions':repetitions,'workloads':manifest(),
            'environment':{'platform':platform.platform(),'python':platform.python_version(),
              'node':subprocess.check_output(['node','--version'],text=True).strip(),
              'playwright':json.loads((ROOT/'node_modules/playwright/package.json').read_text())['version'],
              'cpu':next((x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),None),
              'logical_cpus':os.cpu_count(),'browser':observations[0]['browser']['browser']},
            'method':'Fresh Python process per observation including startup, analysis, HTML and atomic fsync/link. wait4 peak RSS KiB. Fresh Chromium per observation, offline + HTTP abort route, 1280x900. Browser wall timings include automation and two requestAnimationFrame callbacks; startup excluded. AB/BA balanced pairs, warm OS caches, case order rotates. No browser memory or constant total memory claim. Baseline has no page/filter navigation, recorded null. Selection/switch are comparable actions but baseline mounts all text and only its first 100 findings; candidate mounts a page and makes all findings reachable.',
            'summary':summaries,'observations':observations}


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repetitions',type=int,default=6)
    parser.add_argument('--record',type=Path)
    args = parser.parse_args()
    if platform.system()!='Linux': parser.error('Linux required for RSS units')
    if args.repetitions < 6 or args.repetitions > 12 or args.repetitions % 2: parser.error('use 6, 8, 10 or 12 balanced repetitions')
    result = json.dumps(run(args.repetitions),indent=2,sort_keys=True)+'\n'
    if args.record: args.record.write_text(result)
    else: print(result,end='')
