"""Hint prompts preserve transformed content and evidence cannot change silently."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments/comprehension'))
import hints
import evaluate as base


class HintProtocolTests(unittest.TestCase):
    def test_schedule_and_content(self):
        schedule = hints.plan()
        self.assertEqual(len(schedule), 128)
        self.assertEqual(len({(r['id'], l) for r, l in schedule}), 128)
        for row, layout in schedule:
            text = hints.payload(row, layout)['prompt']
            original = base.prompt(row, layout)
            self.assertEqual(text[text.index('Passage: '):], original[original.index('Passage: '):])
            self.assertIn(layout.capitalize() + ' layout was active', text)
            self.assertNotIn('mapping table', text)

    def test_manifest(self):
        hints.check_manifest(hints.OUTPUT)

    def test_reject_unterminated_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'protocol.json').write_bytes((hints.OUTPUT / 'protocol.json').read_bytes())
            (root / 'responses.jsonl').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Unterminated'):
                hints.verify(root)

    def test_reject_changed_real_evidence(self):
        path = hints.OUTPUT / 'responses.jsonl'
        if not path.exists():
            self.skipTest('No real inference evidence yet')
        records = [json.loads(line) for line in path.read_text().splitlines()]
        hints.validate(records)
        for field, value in [('id', -1), ('correct', not records[0]['correct']),
                             ('condition', 'clean'), ('prompt_sha256', 'altered')]:
            altered = copy.deepcopy(records)
            altered[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                hints.validate(altered)
        if len(records) > 1:
            with self.assertRaises(ValueError):
                hints.validate(records[::-1])


if __name__ == '__main__':
    unittest.main()
