# Does an open model understand keyboard-transformed text?

This experiment evaluates **Qwen2.5-1.5B-Instruct, Q4_K_M**, on real public
BoolQ examples, using CPU-only llama.cpp. It complements the deterministic
converter; successful decoding alone is not evidence of model understanding.
No novelty is claimed for robustness evaluation, keyboard substitutions or BoolQ.

## Observed result

All 384 real inference calls completed. There were no invalid answers or
truncated prompts. Total request wall time was **7,771.3 seconds (129.5 minutes)**,
excluding setup and the interruption described below.

| Condition | Correct | Accuracy (Wilson 95% interval) | Paired difference vs clean (bootstrap 95% interval) |
| --- | --- | --- | --- |
| Clean | 45/64 | 70.3% (58.2–80.1%) | — |
| Colemak | 33/64 | 51.6% (39.6–63.4%) | −18.75 points (−31.25 to −6.25) |
| Dvorak | 33/64 | 51.6% (39.6–63.4%) | −18.75 points (−31.25 to −6.25) |
| Decoded Colemak | 45/64 | 70.3% (58.2–80.1%) | 0 points (0 to 0) |
| Decoded Dvorak | 45/64 | 70.3% (58.2–80.1%) | 0 points (0 to 0) |
| Question only | 39/64 | 60.9% (48.7–71.9%) | −9.38 points (−26.56 to +9.38) |

On this sample, both transformations reduced task accuracy by 12 answers. Each
lost 16 clean-correct answers and gained 4 clean-incorrect answers; each exact
McNemar p-value is 0.01182, unadjusted for multiple comparisons. Colemak produced
61 Yes answers and Dvorak 63, out of 64 balanced examples: these near-chance
scores accompany strong answer bias, not robust recovery of the transformed
content. This does not establish that every correct transformed answer was a
guess or that the model can never read such text.

Both independently inferred decoded controls matched **all 64 clean predictions**.
Known-layout deterministic recovery restored the original input and behavior;
this is evidence for the external decoder pipeline, not learned decoding by the
model. The clean baseline only narrowly passed the frozen gate. Its advantage
over question-only is uncertain (the paired interval includes zero), so this
small pilot cannot establish how much clean accuracy depends on the passage.
Contamination, prior knowledge, tokenization and instruction-following remain
possible contributors. See the [interactive offline report](../../results/comprehension/comparison.html)
for every prompt/response and the remaining limitations below.

## Frozen protocol

The protocol and sample were fixed before inspecting inference outcomes.
`inputs.json` contains 64 examples from the BoolQ validation/development split,
32 with each label. Eligible examples have a passage of at most 1,200 characters
and printable ASCII passage/question text. No truncation or normalization is
performed. Within each label, choose the first 32 rows sorted by SHA-256 of
`20261019:<zero-based upstream row index>`, then sort selected rows by index.
This is a small, balanced, short-text subset, **not** a representative estimate
of full BoolQ accuracy. Eligibility and upstream file hash are in the fixture.

First run all 64 clean prompts. The predeclared usable-baseline requirement is
at least 70% accuracy and a Wilson 95% lower confidence bound greater than 50%.
If this fails, stop and record a prerequisite failure; do not interpret layout
scores or select a more flattering sample. There is no tuning on these answers.

After the gate, run five additional conditions for each identical example:

- `colemak` and `dvorak`: map both the passage and question from intended QWERTY
  to the named observed layout using the existing converter's pinned ANSI,
  base/Shift key-position mappings. The English task instruction and field
  labels remain clean. The model receives no mapping table or layout hint.
- `decoded_colemak` and `decoded_dvorak`: deterministically reverse each
  transformation before model inference. Assert byte-for-byte equality with
  clean text, but make **separate real inference calls**, not copied scores.
- `question_only`: retain the clean question and replace the passage with
  `[Passage withheld]`. This checks the role of prior knowledge/question cues
  in the clean task, not transformed-question comprehension.

The five post-gate conditions rotate order by example index. Clean prompts
are necessarily first because they gate the experiment. Request prompt caching
is disabled; actual cache/timing fields remain in the raw evidence. No chat
history is carried between examples. Inference is greedy (`temperature=0`),
seed 20261019, at most 8 generated tokens, context 4096, one server slot, four
CPU threads, no GPU layers. Stop on `<|im_end|>` or `<|endoftext|>`.
The runner rejects truncation/context overflow and enforces a four-hour default
budget between requests (each HTTP call also times out after 180 seconds).
A timeout/runtime failure leaves partial evidence and is not a completed study.

Exact serialized ChatML prompts are retained in each record. The system message
is `Answer the yes/no question using the passage. Reply with exactly Yes or No, without explanation.`
The user message is `Passage: {passage}\nQuestion: {question}\nAnswer:`.
Labels never enter prompts. The parser accepts only case-insensitive `Yes` or
`No`, surrounding whitespace and one optional final period/exclamation mark.
Anything else is invalid and scored incorrect. No answer extraction or repair.
The target is agreement with frozen dataset labels, not current factual truth.

Accuracy uses Wilson 95% intervals. Differences are condition minus clean,
paired by upstream row index. Percentile intervals resample the 64 **paired
example differences** 10,000 times with Python Random seed 20261019. Exact
McNemar two-sided p-values are also reported, unadjusted for multiple comparisons.
These intervals describe item variation under this sampling design, not model
stochasticity, training uncertainty or population-wide performance. A zero-width
decoded-control interval is expected if every decoded prompt produces the same
prediction as clean; it is not a universal guarantee of determinism.

## Sources and licenses

- [BoolQ authors' repository](https://github.com/google-research-datasets/boolean-questions)
  and [Clark et al., 2019](https://arxiv.org/abs/1905.10044): naturally occurring
  yes/no questions with Wikipedia passages. Source and adaptations here are
  **CC BY-SA 3.0**, attributed to Christopher Clark, Kenton Lee, Ming-Wei Chang,
  Tom Kwiatkowski, Michael Collins and Kristina Toutanova. See
  [license](https://creativecommons.org/licenses/by-sa/3.0/).
  `inputs.json`, excerpted prompts in responses/report, and their layout
  transformations retain this license; the project MIT license does not
  replace it. Transformations are modifications, not original dataset text.
- [Pinned public mirror](https://huggingface.co/datasets/google/boolq/tree/35b264d03638db9f4ce671b711558bf7ff0f80d5),
  `data/validation-00000-of-00001.parquet`. The original Google Storage download
  returned HTTP 403 in this environment; this public mirror succeeded without
  credentials. There are 3,270 upstream validation rows.
- [Official Qwen GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/91cad51170dc346986eccefdc2dd33a9da36ead9),
  Apache-2.0; `qwen2.5-1.5b-instruct-q4_k_m.gguf`.
  [Qwen2.5 report](https://arxiv.org/abs/2412.15115) provides model-family context;
  it is not evidence for this experiment's results.
- [llama.cpp b11723](https://github.com/ggml-org/llama.cpp/releases/tag/b11723),
  MIT, Linux x86-64 CPU release, build commit `31288c9c6`.
- [Mapping provenance](../../THIRD_PARTY.md): xkeyboard-config 2.41,
  `2426c5997e9f76a45df2016d1092bff360712e70`; mapping behavior is shared with the
  existing tested application, not a new approximate character cipher.

Reported seconds sum per-request wall times, including HTTP/JSON overhead but
excluding downloads, server startup and sample preparation. Raw server timings
and token counts are retained separately. Browser asset preparation overlapped
some early requests; no controlled runtime comparison is claimed.

Model/binary SHA-256 hashes and environment are in `environment.json`.
Weights and runtime binaries are **not** included in the repository.
The archived run was interrupted after 315 responses and resumed with freshly
downloaded, hash-verified copies of the same model and runtime and the same
server settings. The original 315-response prefix is preserved byte-for-byte;
its hash is recorded in `environment.json` and checked by `verify.py`. Reported
request time excludes the interruption and setup for resumption.

## Reproduce and inspect

Python 3.10+ is sufficient to run the evaluation against a local llama.cpp server
and to verify saved evidence. Asset extraction requires Python 3.12+ (tested: 3.12.3). The tested binary needs compatible Linux x86-64.
Download the pinned assets to an external cache (about 1.1 GiB model plus runtime):

```sh
python3 experiments/comprehension/assets.py /tmp/keyboard-eval
/tmp/keyboard-eval/llama-b11723/llama-server \
  -m /tmp/keyboard-eval/model.gguf -c 4096 -t 4 -ngl 0 \
  --host 127.0.0.1 --port 8091 --parallel 1
# In another terminal, from the repository root:
python3 experiments/comprehension/evaluate.py --output /tmp/keyboard-comprehension-rerun
```

Only asset preparation needs network access. Inference contacts localhost only.
The evaluator refuses to overwrite existing response evidence. Run in a new
output directory. To continue an interrupted run with the same verified model,
runtime and server settings, add `--resume` with the original output directory.
This validates the saved records as an intact prefix of the frozen schedule and
appends only missing calls. It rejects corrupt, altered or reordered records;
it never silently truncates a partial line. The time budget applies to each
invocation, so the caller must also enforce the overall execution deadline.
The measured worker had a one-CPU-equivalent cgroup quota despite four visible
processors and four inference threads. Expect substantial CPU time on a shared VM; timing is not a
hardware benchmark. Compare numerical outcomes rather than byte-identical
response files (timestamps, timings and model paths vary).

Inspect the saved [comparison report](../../results/comprehension/comparison.html)
by opening that file in a browser. It contains every prompt and response plus
paired accuracy intervals. Raw `responses.jsonl` and derived `summary.json` are
beside it. For regeneration and focused offline verification:

```sh
python3 experiments/comprehension/verify.py
python3 -m unittest discover -s tests -p test_comprehension.py
```

To reconstruct the sample from upstream, download the pinned Parquet above,
install `pyarrow==23.0.1` in a disposable environment, and run:

```sh
python3 experiments/comprehension/freeze.py /path/to/validation.parquet /tmp/inputs.json
cmp /tmp/inputs.json experiments/comprehension/inputs.json
```

PyArrow is needed only for this reconstruction, not evaluation or verification.
For the additional browser check, install the repository's pinned Playwright
prerequisites as described in the root README, then run
`node experiments/comprehension/verify_browser.cjs`. Set
`PLAYWRIGHT_BROWSERS_PATH` if using a nondefault browser cache. The check opens
the saved report offline and exercises its native expandable examples.

## Interpretation limits

Both question and passage are transformed. A decline measures failure on this
combined input change; it does not isolate passage comprehension, decoding,
instruction following, tokenization cost or prior knowledge. Accuracy alone
cannot prove internal understanding. These old public examples may have occurred
in model training; contamination was not measured. Question-only performance
helps reveal this concern but cannot rule it out. BoolQ text/labels may be noisy
or outdated. Clean/decoded identical prompts test an external decoder pipeline,
not a learned ability to reverse layouts. One small quantized model, two layouts,
one fixed prompt and short ASCII inputs cannot support claims about all LLMs,
Unicode, other layouts or real user typing errors. Shared-host contention and
unequal token lengths confound runtime comparisons.
