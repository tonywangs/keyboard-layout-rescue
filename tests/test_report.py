import copy
import hashlib
import json
from pathlib import Path
import random
import unittest
from baseline.core import analyze as baseline_analyze
from baseline.report import json_text as baseline_json
from keyboard_rescue.core import analyze
from keyboard_rescue.report import html_text, json_text
from report_workloads import CASES, manifest

ROOT = Path(__file__).resolve().parent


def unpack_html(html):
    """Independent decoder of documented transport; compare whole public schema."""
    data = json.loads(html.split('<script type="application/json" id="report-data">')[1].split('</script>')[0])
    assert data['html_format'] == 1
    report = data['report']
    for candidate in report['candidates']:
        rows = []
        for index, byte, line, column, type_id in candidate['diagnostics']:
            character, kind, choices = data['diagnostic_types'][type_id]
            rows.append(dict(index=index, byte_offset=byte, line=line, column=column,
                             character=character, kind=kind, choices=choices))
        candidate['diagnostics'] = rows
        candidate['changed_spans'] = [dict(start=a,end=b) for a,b in candidate['changed_spans']]
    return report


class ReportTests(unittest.TestCase):
    def test_frozen_baseline_and_workloads(self):
        provenance = json.loads((ROOT/'baseline/provenance.json').read_text())
        self.assertEqual(provenance['catalog_tree'],provenance['verified_local_tree'])
        for name, digest in provenance['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/'baseline'/name).read_bytes()).hexdigest(),digest,name)
        self.assertEqual(manifest(),json.loads((ROOT/'workloads.json').read_text()))

    def test_240_seeded_full_schema_comparisons(self):
        rng = random.Random(2026092722)
        layouts = ('qwerty','colemak','dvorak')
        alphabet = ''.join(chr(i) for i in range(32,127))+'\t\r\n🙂é\u0301\x00\u202e\ufeff'
        count = 0
        for geometry in ('ansi','iso'):
            for source in layouts:
                for target in layouts:
                    if source == target: continue
                    for trial in range(20):
                        text = ''.join(rng.choice(alphabet) for _ in range(rng.randrange(1,500)))
                        spans = None if trial % 2 else [(0,max(1,len(text)//2))]
                        expected = baseline_analyze(text,source,[target],geometry,spans)
                        actual = analyze(text,source,[target],geometry,spans)
                        before = copy.deepcopy(actual)
                        html = html_text(actual)
                        self.assertEqual(actual,expected)
                        self.assertEqual(json_text(actual),baseline_json(expected))
                        self.assertEqual(unpack_html(html),expected)
                        self.assertEqual(html,html_text(actual))
                        self.assertEqual(actual,before)
                        count += 1
        self.assertEqual(count,240)

    def test_frozen_suite_size_determinism_and_complete_diagnostics(self):
        for name,(text,geometry) in CASES.items():
            with self.subTest(case=name):
                expected = baseline_analyze(text,'qwerty',['colemak','dvorak'],geometry)
                html = html_text(expected)
                self.assertLess(len(html.encode()),10*1024*1024)
                self.assertEqual(html,html_text(expected))
                self.assertEqual(unpack_html(html),expected)
                # Independently derive all coordinates, including CRLF and supplementary Unicode.
                coordinates = []
                line,column,byte = 1,1,0
                for char in text:
                    coordinates.append((byte,line,column))
                    byte += len(char.encode())
                    line,column = (line+1,1) if char=='\n' else (line,column+1)
                for candidate in expected['candidates']:
                    for d in candidate['diagnostics']:
                        self.assertEqual((d['byte_offset'],d['line'],d['column']),coordinates[d['index']])
                self.assertEqual(json_text(analyze(text,'qwerty',['colemak','dvorak'],geometry)),baseline_json(expected))

    def test_three_candidates_at_input_limit(self):
        for text in ('<'*65536, 'e '*32768, ''.join(chr(i) for i in range(0x10000,0x14000))):
            report = analyze(text,'qwerty',['qwerty','colemak','dvorak'],'iso')
            html = html_text(report)
            self.assertLess(len(html.encode()),10*1024*1024)
            self.assertEqual(unpack_html(html),report)
