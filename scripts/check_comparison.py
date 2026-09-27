#!/usr/bin/env python3
"""Validate saved paired observations against current and frozen artifacts."""
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))
from report_workloads import CASES, manifest
from keyboard_rescue.core import analyze
from keyboard_rescue.report import html_text
from baseline.core import analyze as baseline_analyze
from baseline.report import html_text as baseline_html


def main():
    result = json.loads((ROOT/'results/report-comparison.json').read_text())
    assert result['workloads'] == manifest()
    repetitions = result['repetitions']
    assert repetitions >= 6 and repetitions % 2 == 0
    assert len(result['observations']) == len(CASES)*2*repetitions
    for case,(text,geometry) in CASES.items():
        for variant, convert, render in [('baseline',baseline_analyze,baseline_html),('candidate',analyze,html_text)]:
            artifact = render(convert(text,'qwerty',['colemak','dvorak'],geometry)).encode()
            digest = hashlib.sha256(artifact).hexdigest()
            rows = [r for r in result['observations'] if r['case']==case and r['variant']==variant]
            assert sorted(r['repetition'] for r in rows)==list(range(1,repetitions+1))
            for row in rows:
                assert row['pair_order']==(['baseline','candidate'] if row['repetition'] % 2 else ['candidate','baseline'])
                assert row['artifact_sha256']==digest and row['artifact_bytes']==len(artifact), (case,variant,'artifact drift')
                assert row['generation']['returncode']==0 and not row['generation']['stderr']
                assert row['browser']['external_requests']==0
                if variant=='candidate':
                    assert len(artifact)<10*1024*1024
                    for state in ('selected_dom','final_dom'):
                        assert row['browser'][state]['diagnostic_rows']<=100
                        assert row['browser'][state]['text_codepoints']<=2000
            summary = result['summary'][case][variant]
            assert summary['artifact_bytes']==len(artifact)
            for field,source,key in [('median_generation_seconds','generation','wall_seconds'),('median_peak_rss_kib','generation','peak_rss_kib')]:
                assert summary[field]==statistics.median(r[source][key] for r in rows)
            for key in ('load_ms','select_ms','switch_ms','text_next_ms','diagnostic_next_ms','filter_ms'):
                values = [r['browser'][key] for r in rows if r['browser'][key] is not None]
                assert summary['median_'+key]==(statistics.median(values) if values else None)
    print(f'Paired evidence: {len(result["observations"])} observations, balanced orders, summaries and all current/baseline artifact hashes verified.')


if __name__=='__main__': main()
