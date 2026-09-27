#!/usr/bin/env python3
"""Bounded end-to-end Linux measurements; no generated reports are retained.

Each sample launches a fresh CLI process, writes and fsyncs a private output file,
then records actual wall time and wait4 peak child RSS. Inputs are deterministic.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'small_recovery': (b'hkuu; w;sug\n' * 8, 'ansi'),
    'large_alternating_spans': (b'e ' * 32768, 'ansi'),
    'large_iso_ambiguity': (b'<' * 65536, 'iso'),
    'large_unsupported_unicode': ('🙂'.encode() * 16384, 'ansi'),
}


def benchmark(repetitions):
    rows = []
    with tempfile.TemporaryDirectory(prefix='keyboard-rescue-benchmark-') as folder:
        work = Path(folder)
        for name,(data,geometry) in CASES.items():
            source = work/'input.txt'
            source.write_bytes(data)
            for format_name in ('text','json','html'):
                timings, peaks, sizes, hashes = [],[],[],[]
                for _ in range(repetitions):
                    destination = work/'output'
                    args = [sys.executable,'-m','keyboard_rescue',str(source),'--observed','qwerty','--intended','colemak',
                            '--geometry',geometry,'--format',format_name,'-o',str(destination)]
                    if format_name!='text': args += ['--intended','dvorak']
                    measured = json.loads(subprocess.check_output(
                        [sys.executable,str(ROOT/'scripts/measure_process.py'),*args],cwd=ROOT,text=True))
                    assert measured['returncode'] == (3 if name in ('large_iso_ambiguity','large_unsupported_unicode') else 0), (args,measured['stderr'])
                    timings.append(measured['wall_seconds'])
                    peaks.append(measured['peak_rss_kib'])
                    sizes.append(destination.stat().st_size)
                    digest = hashlib.sha256()
                    with destination.open('rb') as artifact:
                        while chunk := artifact.read(1024*1024): digest.update(chunk)
                    hashes.append(digest.hexdigest())
                    destination.unlink()
                assert len(set(hashes))==1, 'nondeterministic artifact'
                assert source.read_bytes()==data, 'input changed'
                rows.append({'case':name,'format':format_name,'input_bytes':len(data),
                             'input_sha256':hashlib.sha256(data).hexdigest(),'geometry':geometry,
                             'candidate_count':1 if format_name=='text' else 2,
                             'wall_seconds':timings,'median_wall_seconds':statistics.median(timings),
                             'peak_rss_kib':peaks,'artifact_bytes':sizes[0],'artifact_sha256':hashes[0]})
    return {'schema_version':'1.0','platform':platform.platform(),'python':platform.python_version(),
            'measurement':'Fresh process wall time including startup and fsynced export; wait4 ru_maxrss in KiB from a fresh minimal supervisor; warm filesystem cache; no browser memory measurement.',
            'repetitions':repetitions,'results':rows}


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record',type=Path,help='write measurements to this JSON path instead of stdout')
    parser.add_argument('--repetitions',type=int,default=3)
    args = parser.parse_args()
    if platform.system()!='Linux': parser.error('wait4 RSS units in this benchmark require Linux')
    if not 1 <= args.repetitions <= 5: parser.error('repetitions must be 1 through 5')
    data = json.dumps(benchmark(args.repetitions),indent=2,sort_keys=True)+'\n'
    if args.record: args.record.write_text(data)
    else: print(data,end='')
