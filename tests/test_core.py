import json
from pathlib import Path
import random
import unittest
from keyboard_rescue.core import analyze, convert, MAX_INPUT_BYTES
from keyboard_rescue.layouts import LAYOUTS, mapping, REVISION
from keyboard_rescue.report import html_text, json_text

FIXTURE = json.loads(Path(__file__).with_name('xkb_outputs.json').read_text())


class MappingTests(unittest.TestCase):
    def test_every_supported_key_and_shift_against_independent_fixture(self):
        self.assertEqual(REVISION, FIXTURE['revision'])
        for layout in LAYOUTS:
            expected = FIXTURE['outputs'][layout]
            self.assertEqual({k:list(v) for k,v in mapping(layout,'iso').items()}, expected)
            self.assertEqual(len(mapping(layout)), 48)
            self.assertEqual(len(mapping(layout,'iso')), 49)

    def test_600_seeded_sequences_all_six_directed_pairs_both_geometries(self):
        rng = random.Random(20260927)
        count = 0
        for geometry in ('ansi','iso'):
            for observed in LAYOUTS:
                for intended in LAYOUTS:
                    if observed == intended:
                        continue
                    source = FIXTURE['outputs'][observed]
                    target = FIXTURE['outputs'][intended]
                    keys = [k for k in source if geometry == 'iso' or k != 'LSGT']
                    inverse = {}
                    for key in keys:
                        for level in range(2):
                            inverse.setdefault(source[key][level], []).append((key,level))
                    for _ in range(50):
                        states = [(rng.choice(keys), rng.randrange(2)) for _ in range(rng.randrange(1,160))]
                        text = ''.join(source[k][s] for k,s in states)
                        # Include layout-independent separators, unsupported Unicode and ambiguous ISO chars.
                        text += '\t\r\n<>-_é🙂\u0301'
                        result = convert(text, observed, intended, geometry)
                        expected = []
                        conflicts, unsupported = [], []
                        for i, char in enumerate(text):
                            if char in ' \t\r\n':
                                expected.append(char)
                                continue
                            alternatives = {target[k][s] for k,s in inverse.get(char, [])}
                            expected.append(next(iter(alternatives)) if len(alternatives)==1 else char)
                            if not alternatives:
                                unsupported.append(i)
                            elif len(alternatives)>1:
                                conflicts.append(i)
                        self.assertEqual(result['text'], ''.join(expected))
                        self.assertEqual([d['index'] for d in result['diagnostics'] if d['kind']=='ambiguous'], conflicts)
                        self.assertEqual([d['index'] for d in result['diagnostics'] if d['kind']=='unsupported'], unsupported)
                        covered = {i for s in result['changed_spans'] for i in range(s['start'],s['end'])}
                        self.assertEqual(covered, {i for i,(a,b) in enumerate(zip(text,expected)) if a!=b})
                        self.assertEqual(result['unresolved_characters'], len(conflicts)+len(unsupported))
                        count += 1
        self.assertEqual(count, 600)

    def test_ansi_roundtrip_every_character(self):
        text = ''.join(chr(i) for i in range(32,127)) + '\t\r\n'
        for source in LAYOUTS:
            for target in LAYOUTS:
                candidate = convert(text, source,target)
                self.assertFalse(candidate['diagnostics'])
                self.assertEqual(convert(candidate['text'],target,source)['text'],text)

    def test_worked_recovery(self):
        self.assertEqual(convert('hkuu; w;sug', 'qwerty', 'colemak')['text'], 'hello world')
        self.assertEqual(convert('hello world', 'colemak', 'qwerty')['text'], 'hkuu; w;sug')

    def test_ambiguous_iso_preserved_with_all_alternatives(self):
        result = convert('<>', 'qwerty', 'dvorak', 'iso')
        self.assertEqual(result['text'], '<>')
        self.assertEqual(result['mapping_status'], 'unresolved')
        self.assertEqual({x['output'] for x in result['diagnostics'][0]['choices']}, {'W','<'})
        self.assertEqual({x['key'] for x in result['diagnostics'][0]['choices']}, {'AB08','LSGT'})
        agreed = convert('<>', 'qwerty','qwerty','iso')
        self.assertEqual([d['kind'] for d in agreed['diagnostics']],['convergent','convergent'])
        self.assertEqual(agreed['unresolved_characters'],0)
        self.assertEqual(convert('-_', 'colemak','dvorak','iso')['text'],'-_')

    def test_unicode_offsets_and_separators(self):
        text = 'é🙂\r\n\t\x00\u202e\ufeffe\u0301'
        report = analyze(text,'qwerty',['colemak'])
        diagnostics = report['candidates'][0]['diagnostics']
        self.assertEqual([(d['index'],d['byte_offset'],d['line'],d['column']) for d in diagnostics],
                         [(0,0,1,1),(1,2,1,2),(5,9,2,2),(6,10,2,3),(7,13,2,4),(9,17,2,6)])
        self.assertEqual(report['original'],text)
        self.assertEqual(report['candidates'][0]['text'],text[:-2]+'f\u0301')

    def test_mixed_layout_spans(self):
        text = 'Keep this: hkuu; w;sug. é'
        report = analyze(text,'qwerty',['colemak'],spans=[(11,22)])
        self.assertEqual(report['candidates'][0]['text'], 'Keep this: hello world. é')
        self.assertEqual(report['excluded_characters'], len(text)-11)
        self.assertFalse(report['candidates'][0]['diagnostics'])
        # No automatic segmentation: converting all text also changes the correct prefix.
        self.assertNotEqual(convert(text,'qwerty','colemak')['text'][:11],text[:11])
        self.assertEqual(convert('hkuu; + w;sug','qwerty','colemak',spans=[(8,13),(0,5)])['text'],'hello + world')

    def test_invalid_spans_and_layouts(self):
        for spans in ([],[(0,0)],[(-1,1)],[(0,4)],[(0,2),(1,3)]):
            with self.assertRaises(ValueError):
                analyze('abc','qwerty',['colemak'],spans=spans)
        for source, targets in [('invalid',['qwerty']),('qwerty',[]),('qwerty',['colemak','colemak'])]:
            with self.assertRaises(ValueError):
                analyze('abc',source,targets)

    def test_empty_input_and_bounded_input(self):
        self.assertEqual(analyze('','qwerty',['dvorak'])['candidates'][0]['text'],'')
        analyze('a'*MAX_INPUT_BYTES,'qwerty',['dvorak'])
        with self.assertRaises(ValueError):
            analyze('é'*(MAX_INPUT_BYTES//2+1),'qwerty',['dvorak'])

    def test_deterministic_versioned_serialization_and_hostile_data(self):
        text = '</script><img src="https://example.invalid/x" onerror="alert(1)"> & \u2028🙂'
        report = analyze(text,'qwerty',['dvorak','colemak'])
        serialized = json_text(report)
        self.assertEqual(json.loads(serialized),report)
        self.assertEqual(serialized,json_text(analyze(text,'qwerty',['dvorak','colemak'])))
        self.assertEqual(report['schema_version'],'1.0')
        html = html_text(report)
        self.assertEqual(html,html_text(report))
        data = html.split('<script type="application/json" id="report-data">')[1].split('</script>')[0]
        self.assertNotIn('<',data)
        from test_report import unpack_html
        self.assertEqual(unpack_html(html),report)
