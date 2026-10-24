"""Resumable post-hoc layout-hint control; original evidence is read-only."""
import argparse
import json
import os
import time
from pathlib import Path

import evaluate as base

OUTPUT = base.ROOT / 'results/comprehension-hints'
ARCHIVE = base.ROOT / 'results/comprehension/responses.jsonl'
LAYOUTS = ('colemak', 'dvorak')


def payload(row, layout):
    text = base.prompt(row, layout)
    hint = (f'The passage and question were typed on intended QWERTY keys while the '
            f'{layout.capitalize()} layout was active. Recover the intended English '
            'by matching physical key positions, then answer the question.\n')
    text = text.replace('Passage: ', hint + 'Passage: ', 1)
    return dict(prompt=text, n_predict=8, temperature=0, seed=base.SEED,
                cache_prompt=False, stop=['<|im_end|>', '<|endoftext|>'])


def plan():
    rows = json.loads(base.INPUTS.read_text())['rows']
    return [(row, layout) for i, row in enumerate(rows)
            for layout in (LAYOUTS if i % 2 == 0 else LAYOUTS[::-1])]


def validate(records):
    schedule = plan()
    if len(records) > len(schedule):
        raise ValueError('Too many hint records')
    for record, (row, layout) in zip(records, schedule):
        response = record['response']
        request = payload(row, layout)
        prediction = base.parse(response['content'])
        if not (record['id'] == row['id'] and record['condition'] == 'hint_' + layout
                and record['request'] == request
                and record['prompt_sha256'] == base.digest(request['prompt'].encode())
                and response['prompt'] == request['prompt']
                and not response['truncated'] and response['timings']['cache_n'] == 0
                and 0 < response['tokens_evaluated'] < 4088
                and 0 < response['tokens_predicted'] <= 8
                and response['generation_settings']['temperature'] == 0
                and response['generation_settings']['seed'] == base.SEED
                and record['prediction'] is prediction
                and record['correct'] == (prediction is not None and prediction == row['answer'])
                and record['wall_seconds'] > 0):
            raise ValueError('Hint evidence differs from frozen schedule or protocol')


def check_manifest(output):
    manifest = json.loads((output / 'protocol.json').read_text())
    if manifest['inputs_sha256'] != base.digest(base.INPUTS.read_bytes()):
        raise ValueError('Inputs changed')
    if manifest['original_responses_sha256'] != base.digest(ARCHIVE.read_bytes()):
        raise ValueError('Original evidence changed')
    if manifest['prompts_sha256'] != base.digest(json.dumps(
            [payload(row, layout) for row, layout in plan()], sort_keys=True).encode()):
        raise ValueError('Frozen hint prompts changed')
    return manifest


def verify(output, require_complete=False):
    check_manifest(output)
    raw = (output / 'responses.jsonl').read_bytes()
    if raw and not raw.endswith(b'\n'):
        raise ValueError('Unterminated evidence record; preserve and inspect before resuming')
    records = [json.loads(line) for line in raw.splitlines()]
    validate(records)
    if require_complete and len(records) != len(plan()):
        raise ValueError('Hint experiment incomplete')
    print(f'PASS: {len(records)}/{len(plan())} hint responses; ' +
          ('complete' if len(records) == len(plan()) else 'partial evidence, no full-sample conclusion'))
    return records


def run(args):
    check_manifest(args.output)
    records = verify(args.output) if (args.output / 'responses.jsonl').exists() else []
    start = time.monotonic()
    for row, layout in plan()[len(records):len(records) + args.max_calls]:
        if time.monotonic() - start >= args.max_seconds:
            break
        request = payload(row, layout)
        before = time.monotonic()
        response = base.request(args.endpoint, request)
        prediction = base.parse(response['content'])
        record = dict(id=row['id'], condition='hint_' + layout, request=request,
                      response=response, prompt_sha256=base.digest(request['prompt'].encode()),
                      prediction=prediction, correct=prediction is not None and prediction == row['answer'],
                      wall_seconds=time.monotonic() - before)
        validate(records + [record])
        with (args.output / 'responses.jsonl').open('a') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        records.append(record)
        print(f'{len(records)}/128: {row["id"]} hint_{layout}', flush=True)
    verify(args.output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--endpoint', default='http://127.0.0.1:8091')
    parser.add_argument('--max-calls', type=int, default=16)
    parser.add_argument('--max-seconds', type=int, default=900)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    if args.max_calls < 1 or args.max_seconds < 1:
        parser.error('Budgets must be positive')
    if args.verify:
        verify(args.output, args.require_complete)
    else:
        run(args)
