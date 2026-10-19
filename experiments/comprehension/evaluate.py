"""Bounded local CPU evaluation. Standard library only; see README.md."""
import argparse
import hashlib
import html
import json
import math
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from keyboard_rescue.core import convert

INPUTS = Path(__file__).with_name('inputs.json')
CONDITIONS = ('clean', 'colemak', 'dvorak', 'decoded_colemak', 'decoded_dvorak', 'question_only')
SYSTEM = 'Answer the yes/no question using the passage. Reply with exactly Yes or No, without explanation.'
SEED = 20261019

def digest(data):
    return hashlib.sha256(data).hexdigest()

def prompt(row, condition):
    passage, question = row['passage'], row['question']
    if condition == 'question_only':
        passage = '[Passage withheld]'
    elif condition != 'clean':
        layout = condition.removeprefix('decoded_')
        passage = convert(passage, 'qwerty', layout)['text']
        question = convert(question, 'qwerty', layout)['text']
        if condition.startswith('decoded_'):
            passage = convert(passage, layout, 'qwerty')['text']
            question = convert(question, layout, 'qwerty')['text']
            assert (passage, question) == (row['passage'], row['question'])
    user = f'Passage: {passage}\nQuestion: {question}\nAnswer:'
    return f'<|im_start|>system\n{SYSTEM}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n'

def parse(text):
    match = re.fullmatch(r'\s*(yes|no)[.!]?\s*', text, re.I)
    return None if match is None else match[1].lower() == 'yes'

def wilson(k, n):
    p, z = k/n, 1.959963984540054
    center = (p + z*z/(2*n))/(1+z*z/n)
    radius = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [center-radius, center+radius]

def summarize(rows, records):
    by = {(r['id'], r['condition']): r for r in records}
    result = {'n': len(rows), 'conditions': {}, 'paired_vs_clean': {}}
    clean = [by[(r['id'], 'clean')]['correct'] for r in rows]
    for c in CONDITIONS:
        if not all((r['id'], c) in by for r in rows):
            continue
        rs = [by[(r['id'], c)] for r in rows]
        values = [x['correct'] for x in rs]
        k, n = sum(values), len(values)
        result['conditions'][c] = {'correct': k, 'n': n, 'accuracy': k/n, 'wilson_95': wilson(k,n),
            'invalid': sum(x['prediction'] is None for x in rs),
            'predicted_yes': sum(x['prediction'] is True for x in rs),
            'predicted_no': sum(x['prediction'] is False for x in rs),
            'wall_seconds': sum(x['wall_seconds'] for x in rs)}
        if c == 'clean':
            continue
        diffs = [int(a)-int(b) for a,b in zip(values,clean)]
        rng = random.Random(SEED)
        boot = sorted(sum(rng.choices(diffs,k=n))/n for _ in range(10000))
        lost = sum(b and not a for a,b in zip(values,clean))
        gained = sum(a and not b for a,b in zip(values,clean))
        discordant = lost+gained
        p = min(1.0,2*sum(math.comb(discordant,i) for i in range(min(lost,gained)+1))/2**discordant)
        result['paired_vs_clean'][c] = {'difference': sum(diffs)/n, 'paired_bootstrap_95': [boot[249],boot[9749]],
            'lost': lost, 'gained': gained, 'exact_mcnemar_p_unadjusted': p}
    result['baseline_usable'] = sum(clean)/len(clean) >= .70 and wilson(sum(clean),len(clean))[0] > .50
    return result

def request(endpoint, payload):
    req = urllib.request.Request(endpoint+'/completion', json.dumps(payload).encode(), {'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=180) as response:
        return json.load(response)

def schedule(rows):
    pairs = [(row, 'clean') for row in rows]
    rest = CONDITIONS[1:]
    for i, row in enumerate(rows):
        pairs.extend((row, c) for c in rest[i%len(rest):]+rest[:i%len(rest)])
    return pairs

def load_resume(target, rows):
    """Accept only an intact prefix of this exact frozen experiment."""
    environment = json.loads(INPUTS.with_name('environment.json').read_text())
    if digest(INPUTS.read_bytes()) != environment['inputs_sha256']:
        raise ValueError('Frozen inputs changed')
    records = [json.loads(line) for line in target.read_text().splitlines()]
    plan = schedule(rows)
    if len(records) > len(plan):
        raise ValueError('Too many saved records')
    for record, (row, condition) in zip(records, plan):
        text = prompt(row, condition)
        expected = {'prompt': text, 'n_predict': 8, 'temperature': 0, 'seed': SEED,
                    'cache_prompt': False, 'stop': ['<|im_end|>', '<|endoftext|>']}
        response = record['response']
        prediction = parse(response['content'])
        if not (record['id'] == row['id'] and record['condition'] == condition
                and record['request'] == expected and record['prompt_sha256'] == digest(text.encode())
                and response['prompt'] == text and not response['truncated']
                and response['timings']['cache_n'] == 0
                and 0 < response['tokens_evaluated'] < 4088
                and 0 < response['tokens_predicted'] <= 8
                and response['generation_settings']['temperature'] == 0
                and response['generation_settings']['seed'] == SEED
                and record['prediction'] is prediction
                and record['correct'] == (prediction is not None and prediction == row['answer'])
                and record['wall_seconds'] > 0):
            raise ValueError('Saved evidence does not match frozen protocol')
    if len(records) >= len(rows) and not summarize(rows, records)['baseline_usable']:
        raise ValueError('Saved clean baseline failed gate')
    return records

def run(args):
    rows = json.loads(INPUTS.read_text())['rows']
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    target = output/'responses.jsonl'
    if target.exists() and not args.resume:
        raise SystemExit('Refusing existing responses; choose a new output directory.')
    records = load_resume(target, rows) if args.resume else []
    completed = {(r['id'], r['condition']) for r in records}
    start = time.monotonic()
    def infer(row, condition):
        if (row['id'], condition) in completed:
            return
        if time.monotonic()-start > args.max_seconds:
            raise RuntimeError('Bounded evaluation time budget exhausted')
        text = prompt(row, condition)
        payload = {'prompt': text, 'n_predict': 8, 'temperature': 0, 'seed': SEED,
                   'cache_prompt': False, 'stop': ['<|im_end|>', '<|endoftext|>']}
        before = time.monotonic()
        response = request(args.endpoint, payload)
        if response.get('truncated') or response.get('timings',{}).get('prompt_n',0) >= 4088:
            raise RuntimeError('Input truncated or context limit reached')
        prediction = parse(response['content'])
        record = {'id': row['id'], 'condition': condition, 'prompt_sha256': digest(text.encode()),
                  'prediction': prediction, 'correct': prediction is not None and prediction == row['answer'],
                  'wall_seconds': time.monotonic()-before, 'request': payload, 'response': response}
        with target.open('a') as f:
            f.write(json.dumps(record,ensure_ascii=False)+'\n')
        records.append(record)
        print(f"{len(records)} {row['id']} {condition}: {response['content']!r}",flush=True)
    for row in rows:
        infer(row,'clean')
    summary = summarize(rows,records)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if not summary['baseline_usable']:
        raise SystemExit('BLOCKED: clean baseline below predeclared usability threshold')
    # Rotate condition order to avoid always running a layout earlier than its control.
    rest = CONDITIONS[1:]
    for i,row in enumerate(rows):
        order = rest[i%len(rest):]+rest[:i%len(rest)]
        for condition in order:
            infer(row,condition)
    (output/'summary.json').write_text(json.dumps(summarize(rows,records),indent=2)+'\n')
    report(output)

def report(output):
    rows = json.loads(INPUTS.read_text())['rows']
    records = [json.loads(line) for line in (output/'responses.jsonl').read_text().splitlines()]
    summary = summarize(rows,records)
    content = ['<!doctype html><meta charset="utf-8"><title>Keyboard layout comprehension</title>',
        '<style>body{font:16px system-ui;max-width:1100px;margin:2em auto;padding:1em}table{border-collapse:collapse}td,th{padding:.5em;border:1px solid #bbb}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}</style>',
        '<h1>Keyboard layout comprehension: paired CPU evaluation</h1>',
        '<p>64 balanced public BoolQ examples; Qwen2.5-1.5B-Instruct Q4_K_M. These observations measure one model and prompt, not LLMs generally. Decoded controls use deterministic recovery before inference.</p>',
        '<p>See <a href="../../experiments/comprehension/README.md">protocol and limitations</a>. Accuracy intervals are Wilson 95%; paired intervals resample examples 10,000 times. No multiplicity correction.</p>',
        '<table><tr><th>Condition</th><th>Correct</th><th>Accuracy [95% CI]</th><th>Difference vs clean [95% CI]</th><th>Yes / No / invalid</th><th>Seconds</th></tr>']
    for c,v in summary['conditions'].items():
        pair=summary['paired_vs_clean'].get(c)
        delta='—' if pair is None else f"{pair['difference']:+.1%} [{pair['paired_bootstrap_95'][0]:+.1%}, {pair['paired_bootstrap_95'][1]:+.1%}]"
        content.append(f"<tr><td>{c}</td><td>{v['correct']}/{v['n']}</td><td>{v['accuracy']:.1%} [{v['wilson_95'][0]:.1%}, {v['wilson_95'][1]:.1%}]</td><td>{delta}</td><td>{v['predicted_yes']} / {v['predicted_no']} / {v['invalid']}</td><td>{v['wall_seconds']:.1f}</td></tr>")
    content.append('</table>')
    if len(summary['conditions']) == len(CONDITIONS):
        clean = summary['conditions']['clean']['accuracy']
        colemak = summary['conditions']['colemak']['accuracy']
        dvorak = summary['conditions']['dvorak']['accuracy']
        question = summary['conditions']['question_only']['accuracy']
        content.append(f'<h2>What this run establishes</h2><p>Clean accuracy is {clean:.1%}; '
                       f'Colemak {colemak:.1%}; Dvorak {dvorak:.1%}; question-only {question:.1%}. '
                       'The decoded rows measure an external deterministic recovery pipeline followed by model inference. '
                       'They do not show that the model learned to decode. Both question and passage change in the '
                       'transformed rows, so these scores cannot isolate the underlying reason for errors. '
                       'The predeclared clean baseline gate requires at least 70% accuracy and a Wilson lower bound above 50%. '
                       'Public benchmark contamination and reliance on prior knowledge remain possible.</p>')
    else:
        content.append('<h2>Incomplete paired experiment</h2><p>Only the conditions shown above have complete evidence. '
                       'No conclusion about missing conditions is justified.</p>')
    content.append('<h2>Inspect every paired example</h2>')
    for row in rows:
        content.append(f"<details><summary>BoolQ validation row {row['id']} — label {'Yes' if row['answer'] else 'No'}</summary><p>{html.escape(row['question'])}</p><p>{html.escape(row['passage'])}</p>")
        for r in records:
            if r['id']==row['id']:
                content.append(f"<h3>{r['condition']}: {html.escape(r['response']['content'])} ({'correct' if r['correct'] else 'incorrect'})</h3><pre>{html.escape(r['request']['prompt'])}</pre>")
        content.append('</details>')
    content.append('<p>BoolQ excerpts and layout adaptations: Clark et al., CC BY-SA 3.0. <a href="https://github.com/google-research-datasets/boolean-questions">Source and attribution</a>.</p>')
    (output/'comparison.html').write_text('\n'.join(content)+'\n')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--endpoint',default='http://127.0.0.1:8091')
    parser.add_argument('--output',required=True)
    parser.add_argument('--max-seconds',type=int,default=14400)
    parser.add_argument('--report-only',action='store_true')
    parser.add_argument('--resume',action='store_true',help='Validate and append missing calls to an intact saved prefix')
    args=parser.parse_args()
    if args.report_only:
        report(Path(args.output))
    else:
        run(args)
