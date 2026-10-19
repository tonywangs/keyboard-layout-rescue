"""Focused tests of experimental validity, independent of model availability."""
import importlib.util
import json
import unittest
import tempfile
from pathlib import Path

spec=importlib.util.spec_from_file_location('comprehension',Path(__file__).resolve().parents[1]/'experiments/comprehension/evaluate.py')
e=importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)

class ComprehensionTests(unittest.TestCase):
    def test_resume_preserves_prefix_and_rejects_changed_evidence(self):
        rows=json.loads(e.INPUTS.read_text())['rows']
        saved=e.ROOT/'results/comprehension/responses.jsonl'
        prefix=[json.loads(line) for line in saved.read_text().splitlines()[:2]]
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'responses.jsonl'
            def write(records):
                target.write_text(''.join(json.dumps(r)+'\n' for r in records))
            write(prefix)
            before=target.read_bytes()
            self.assertEqual(e.load_resume(target,rows),prefix)
            self.assertEqual(target.read_bytes(),before)
            write(list(reversed(prefix)))
            with self.assertRaises(ValueError):
                e.load_resume(target,rows)
            prefix[0]['request']['prompt']+=' changed'
            write(prefix)
            with self.assertRaises(ValueError):
                e.load_resume(target,rows)
            target.write_text('{partial')
            with self.assertRaises(json.JSONDecodeError):
                e.load_resume(target,rows)

    def test_parser_does_not_extract_explanations(self):
        for s in ('yes',' YES!\n','Yes.'):
            self.assertIs(e.parse(s),True)
        for s in ('no',' No. '):
            self.assertIs(e.parse(s),False)
        for s in ('','Yes or no','Yes because','not yes','No\nYes','Yes!!'):
            self.assertIsNone(e.parse(s))

    def test_frozen_balanced_inputs_and_exact_controls(self):
        rows=json.loads(e.INPUTS.read_text())['rows']
        self.assertEqual(len({r['id'] for r in rows}),64)
        self.assertEqual(sum(r['answer'] for r in rows),32)
        for r in rows:
            clean=e.prompt(r,'clean')
            for layout in ('colemak','dvorak'):
                self.assertEqual(e.prompt(r,'decoded_'+layout),clean)
                self.assertNotEqual(e.prompt(r,layout),clean)
            self.assertNotIn(r['passage'],e.prompt(r,'question_only'))

    def test_wilson_known_endpoints(self):
        lo,hi=e.wilson(0,10)
        self.assertAlmostEqual(lo,0)
        self.assertAlmostEqual(hi,0.2775328,places=6)
        lo,hi=e.wilson(10,10)
        self.assertAlmostEqual(lo,0.7224672,places=6)
        self.assertAlmostEqual(hi,1)

    def test_pairing_uses_ids_and_direction(self):
        rows=[{'id':i} for i in range(8)]
        records=[]
        for i in reversed(range(8)):
            records.extend([{'id':i,'condition':'clean','correct':True,'prediction':True,'wall_seconds':1},
                            {'id':i,'condition':'colemak','correct':False,'prediction':None,'wall_seconds':2},
                            {'id':i,'condition':'decoded_colemak','correct':True,'prediction':True,'wall_seconds':1}])
        summary=e.summarize(rows,records)
        pair=summary['paired_vs_clean']['colemak']
        self.assertEqual((pair['lost'],pair['gained']),(8,0))
        self.assertEqual(pair['difference'],-1)
        self.assertEqual(pair['paired_bootstrap_95'],[-1,-1])
        self.assertEqual(pair['exact_mcnemar_p_unadjusted'],2/256)
        control=summary['paired_vs_clean']['decoded_colemak']
        self.assertEqual(control['difference'],0)
        self.assertEqual(control['exact_mcnemar_p_unadjusted'],1)
        self.assertEqual(summary['conditions']['colemak']['invalid'],8)

    def test_failed_gate(self):
        rows=[{'id':i} for i in range(64)]
        records=[{'id':i,'condition':'clean','correct':i<44,'prediction':True,'wall_seconds':1} for i in range(64)]
        self.assertFalse(e.summarize(rows,records)['baseline_usable'])
        records[44]['correct']=True
        self.assertTrue(e.summarize(rows,records)['baseline_usable'])

if __name__=='__main__':
    unittest.main()
