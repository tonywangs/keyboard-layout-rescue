"""Offline evidence integrity checks; does not rerun inference or require a model."""
import argparse
import json
import tempfile
from pathlib import Path
from evaluate import INPUTS, CONDITIONS, digest, parse, prompt, report, summarize


def verify(output, baseline_only=False):
    fixture=json.loads(INPUTS.read_text())
    environment=json.loads(INPUTS.with_name('environment.json').read_text())
    assert digest(INPUTS.read_bytes())==environment['inputs_sha256'], 'Frozen sample changed'
    rows=fixture['rows']
    by_id={r['id']:r for r in rows}
    assert len(by_id)==len(rows)==64
    assert sum(r['answer'] for r in rows)==32
    for r in rows:
        assert len(r['passage'])<=1200
        assert all(32<=ord(c)<=126 for c in r['question']+r['passage'])
        for c in ('decoded_colemak','decoded_dvorak'):
            assert prompt(r,c)==prompt(r,'clean')
    raw=(output/'responses.jsonl').read_bytes()
    records=[json.loads(line) for line in raw.splitlines()]
    # The archived run resumed after a process interruption; prove that its
    # original observations were retained byte-for-byte. New reruns have
    # different timing bytes and are verified by protocol checks below instead.
    archived=Path(__file__).resolve().parents[2]/'results/comprehension'
    if output.resolve()==archived and 'resumption' in environment:
        resume=environment['resumption']
        prefix=b''.join(raw.splitlines(keepends=True)[:resume['retained_records']])
        assert digest(prefix)==resume['retained_prefix_sha256'], 'Original evidence prefix changed'
    conditions=('clean',) if baseline_only else CONDITIONS
    expected={(r['id'],c) for r in rows for c in conditions}
    assert len(records)==len(expected), 'Incomplete or duplicated inference records'
    assert {(r['id'],r['condition']) for r in records}==expected
    for record in records:
        row=by_id[record['id']]
        text=prompt(row,record['condition'])
        assert record['request']['prompt']==text
        assert record['prompt_sha256']==digest(text.encode())
        assert record['request']=={'prompt':text,'n_predict':8,'temperature':0,'seed':20261019,
                                  'cache_prompt':False,'stop':['<|im_end|>','<|endoftext|>']}
        response=record['response']
        assert response['prompt']==text
        assert not response['truncated']
        assert response['timings']['cache_n']==0
        assert 0<response['tokens_evaluated']<4088
        assert 0<response['tokens_predicted']<=8
        assert response['generation_settings']['temperature']==0
        assert response['generation_settings']['seed']==20261019
        assert record['prediction'] is parse(response['content'])
        assert record['correct']==(record['prediction'] is not None and record['prediction']==row['answer'])
        assert record['wall_seconds']>0
        assert response['timings']['prompt_ms']>0
    calculated=summarize(rows,records)
    assert calculated==json.loads((output/'summary.json').read_text()), 'Summary mismatch'
    if not baseline_only:
        assert calculated['baseline_usable'], 'Unusable clean baseline'
        with tempfile.TemporaryDirectory() as tmp:
            destination=Path(tmp)
            (destination/'responses.jsonl').write_bytes((output/'responses.jsonl').read_bytes())
            report(destination)
            assert (destination/'comparison.html').read_bytes()==(output/'comparison.html').read_bytes()
    print(f'PASS: {len(records)} raw responses, frozen prompts, scoring, paired statistics and '+
          ('baseline evidence' if baseline_only else 'comparison report'))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[2]/'results/comprehension')
    parser.add_argument('--baseline-only',action='store_true')
    args=parser.parse_args()
    verify(args.output,args.baseline_only)
