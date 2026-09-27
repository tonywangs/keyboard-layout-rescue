# Validation evidence

These are actual local measurements and test outputs, not performance targets.

## Correctness and integration

- `tests.log`: the complete offline verifier output. It checks 294 independently generated key/modifier outputs, 20 Python test methods including 600 seeded sequences (seed 20260927; 50 sequences per directed layout pair per geometry), six isolated installed CLI scenarios, and 29 Chromium assertions.
- Browser engine: Chromium 153.0.8010.12 via pinned Playwright 1.63.0. Network access was disabled and HTTP(S) routes were set to abort. Selection by keyboard, actual clipboard access and denied-clipboard fallback, exact UTF-8 downloads, hostile script/markup, mobile width, 32,768 changed spans and capped diagnostic rendering passed.
- Unicode, punctuation, CRLF and mixed-layout examples are explicit. The seeded oracle test independently computes candidate alternatives from native-library outputs; it does not use the application mapping table to derive expectations.
- The installed test uses a fresh environment outside the checkout, isolated Python mode and a tested socket-denial audit hook. No pip, runtime downloads or third-party Python packages are needed.

## Bounded performance experiment

Environment: `Linux-6.8.0-124-generic-x86_64-with-glibc2.39`, Python 3.12.3. Three fresh CLI processes per row. Time includes Python startup, conversion, serialization, file writing and fsync; reported time is the median. Peak RSS is the maximum of the three measured process high-water marks, from `wait4`, in KiB. A fresh minimal measurement supervisor prevents previously allocated benchmark buffers from inflating child RSS. Warm filesystem caches and shared host load affect results. No CPU affinity or cold-cache claim is made.
| Input | Format | Input bytes | Candidates | Median seconds | Peak RSS KiB | Artifact bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| small_recovery | text | 96 | 1 | 0.101012 | 17664 | 96 |
| small_recovery | json | 96 | 2 | 0.097887 | 17664 | 2461 |
| small_recovery | html | 96 | 2 | 0.102720 | 17664 | 14169 |
| large_alternating_spans | text | 65536 | 1 | 0.198439 | 26752 | 65536 |
| large_alternating_spans | json | 65536 | 2 | 0.388101 | 39372 | 2010856 |
| large_alternating_spans | html | 65536 | 2 | 0.399776 | 45340 | 2022564 |
| large_iso_ambiguity | text | 65536 | 1 | 0.280466 | 42364 | 65536 |
| large_iso_ambiguity | json | 65536 | 2 | 1.534489 | 116404 | 25035067 |
| large_iso_ambiguity | html | 65536 | 2 | 1.702409 | 200948 | 27340535 |
| large_unsupported_unicode | text | 65536 | 1 | 0.127158 | 25984 | 65536 |
| large_unsupported_unicode | json | 65536 | 2 | 0.305522 | 42880 | 4506196 |
| large_unsupported_unicode | html | 65536 | 2 | 0.375536 | 56140 | 4517904 |

Raw individual samples, input hashes and deterministic artifact hashes are in [benchmark.json](benchmark.json). Inputs are generated in `scripts/benchmark.py`: 8 repeats of the worked recovery line, 32,768 repeats of `e `, 65,536 ISO `<` characters, and 16,384 emoji. Large reports are generated in temporary storage and deleted; they are not committed.

## Findings and validation limits


The conversion hypothesis is conditional, and deliberately fails to recover uniquely in the ISO punctuation case. Those characters remain unchanged with conflicting alternatives. Unsupported Unicode also remains unchanged. Neither case is classified as fully mapped. This is expected negative evidence, not an error hidden by the tests.

Diagnostics have significant space and memory cost. A 64 KiB ambiguous input produces about 25–27 MB of two-candidate JSON/HTML; HTML assembly temporarily holds multiple serialized strings. No compression or streaming-report claim is made. This supports the conservative 64 KiB input limit. Browser memory was not measured, and the browser suite does not load the largest ambiguity-heavy report; it exercises a full-sized 64 KiB alternating-span input and 200 diagnostic rows with a 100-row display cap.

An initial measurement approach retained large report bytes in the benchmark parent, contaminating later forked-child peak RSS. That approach was replaced with streaming hashes and a fresh measurement supervisor; the committed measurements use the corrected method. The initial worked example also contained an incorrectly transcribed source string; the independent mapping checks exposed it, and the example was corrected before the final passing run.

Failure coverage includes injected partial writes, fsync/link failures, destination creation races, real SIGTERM during staging, invalid UTF-8, byte limits, hardlinks and symlinks. It does not establish power-loss durability, Windows behavior, network-filesystem semantics, or recovery from unmodeled keyboard states. The browser is Chromium only; other browsers may deny clipboard access and use the documented download fallback.
