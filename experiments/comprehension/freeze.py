"""Recreate the fixed sample from the pinned upstream Parquet (requires pyarrow)."""
import hashlib
import json
import sys
from pathlib import Path
import pyarrow.parquet as pq

SEED = 20261019
source = Path(sys.argv[1])
rows = pq.read_table(source).to_pylist()
eligible = [(i, r) for i, r in enumerate(rows)
            if len(r['passage']) <= 1200 and all(32 <= ord(c) <= 126 for c in r['passage'] + r['question'])]
selected = []
for label in (False, True):
    pool = [(i, r) for i, r in eligible if r['answer'] == label]
    pool.sort(key=lambda ir: hashlib.sha256(f'{SEED}:{ir[0]}'.encode()).digest())
    selected.extend({'id': i, **r} for i, r in pool[:32])
selected.sort(key=lambda r: r['id'])
output = {'dataset': 'google/boolq', 'revision': '35b264d03638db9f4ce671b711558bf7ff0f80d5',
          'split': 'validation', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'seed': SEED, 'eligible': len(eligible), 'rows': selected}
Path(sys.argv[2]).write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
