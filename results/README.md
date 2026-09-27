# Validation evidence

These are actual local observations, not performance targets. The historical first-release evidence remains in [benchmark.json](benchmark.json), [baseline-validation.md](baseline-validation.md) and [baseline-tests.txt](baseline-tests.txt). The old worked HTML example is preserved. The current evidence and behavior follow below.

## Correctness and integration

`tests.log` contains the final offline verifier output: 294 native key/modifier outputs, 24 Python test methods, six installed CLI scenarios, and the Chromium assertion count printed there. The mapping oracle retains 600 seeded sequences (seed 20260927). Another 240 inputs (seed 2026092722; 20 per directed layout pair per geometry) compare the complete analysis, unchanged public JSON bytes, and decoded compact HTML against the frozen baseline. Partial selected spans, unsupported Unicode, punctuation and hostile strings are included. Eight frozen workloads also receive lossless round-trip, deterministic-output and size checks. Additional tests stress three candidates at the 64 KiB boundary, including unique supplementary code points.

Chromium runs offline with HTTP(S) requests intercepted and aborted. The browser suite exercises explicit selection by keyboard, real full-text clipboard writes from a partial page, denied-clipboard fallback, exact UTF-8 original/candidate/JSON downloads, all finding filters, direct and sequential navigation, focus, hostile markup, empty input, and the final row of 65,536 ambiguity diagnostics. Independent traversal concatenates every page of a mixed Unicode/CRLF fixture and checks its changed positions and every diagnostic index. At most 100 rows are mounted. Maximum ambiguity exports are checked against the Python analysis, including all alternatives. Automated keyboard/focus checks are not a screen-reader audit or a WCAG conformance claim.

The installed check creates a fresh isolated Python environment outside the checkout, blocks socket operations with a verified audit hook, and checks exact recovered CRLF text and compact report controls. The existing collision, input immutability, write/fsync/link failure, SIGTERM, and native mapping regressions remain in the verifier.

## Six balanced paired repetitions

[report-comparison.json](report-comparison.json) contains all 96 observations: eight workloads × six pairs × two renderers. Recipes and SHA-256 input hashes are frozen in `tests/report_workloads.py` and `tests/workloads.json`. The baseline files and hashes are in `tests/baseline/`; they were copied only after the checkout tree exactly matched the catalog tree. Candidate artifact hashes agree across all six repetitions; every frozen candidate report is below 10 MiB. Generated reports are temporary and are not committed. The offline verifier regenerates both versions and checks their bytes and hashes against the saved observations, verifies balanced orders and recomputes every summary median.

Fresh Python processes include startup, conversion, serialization and atomic fsync/link export. Peak process RSS comes from Linux `wait4` through a fresh minimal supervisor. This is a generation worker, not a timing of CLI argument parsing. Each browser observation starts a fresh Chromium with a 1280×900 viewport, offline mode and blocked HTTP(S). Browser startup is excluded from load time; automation overhead, layout and two animation frames are included. AB/BA order alternates within each workload and workload order rotates each repetition. OS caches are warm; host contention and timing noise are uncontrolled. Medians below are descriptive, not significance tests.

Environment: Linux-6.8.0-124-generic-x86_64-with-glibc2.39; Python 3.12.3; Node v24.20.0; Playwright 1.63.0; Chromium 153.0.8010.12; CPU DO-Regular.

| Workload | HTML bytes, baseline → candidate | Generation ms, baseline → candidate | Peak RSS KiB, baseline → candidate |
| --- | ---: | ---: | ---: |
| ambiguity | 227,873 → 51,307 | 119.0 → 117.2 | 19,130 → 18,560 |
| boundary_alternating | 2,022,564 → 1,111,341 | 444.4 → 467.9 | 45,604 → 43,656 |
| boundary_ambiguity | 27,340,535 → 4,278,369 | 1953.7 → 1378.6 | 200,254 → 92,004 |
| boundary_unicode | 4,517,904 → 1,345,722 | 446.8 → 433.9 | 55,952 → 42,352 |
| hostile | 89,771 → 40,177 | 124.7 → 108.6 | 18,284 → 18,176 |
| ordinary | 17,154 → 21,643 | 105.9 → 106.2 | 17,792 → 17,792 |
| page_edges | 975,156 → 185,944 | 192.4 → 156.0 | 24,416 → 21,312 |
| unicode | 200,077 → 65,219 | 120.3 → 114.0 | 19,264 → 18,688 |

| Workload | Load ms, baseline → candidate | Candidate switch ms, baseline → candidate | Selected DOM elements, baseline → candidate | Candidate next text / findings page ms |
| --- | ---: | ---: | ---: | ---: |
| ambiguity | 217.7 → 178.8 | 93.7 → 115.6 | 1,087 → 1,214 | n/a / 48.6 |
| boundary_alternating | 397.1 → 328.0 | 1735.5 → 129.5 | 65,611 → 2,102 | 108.0 / n/a |
| boundary_ambiguity | 1367.5 → 591.4 | 153.8 → 83.1 | 575 → 702 | 54.1 / 66.2 |
| boundary_unicode | 566.9 → 375.4 | 118.3 → 88.4 | 575 → 702 | 58.0 / 50.1 |
| hostile | 180.6 → 190.2 | 114.1 → 105.7 | 991 → 1,118 | n/a / 71.7 |
| ordinary | 179.6 → 185.5 | 57.7 → 61.9 | 187 → 214 | n/a / n/a |
| page_edges | 281.2 → 190.2 | 93.2 → 85.3 | 579 → 704 | 67.2 / 78.4 |
| unicode | 218.4 → 204.8 | 95.1 → 97.6 | 575 → 702 | n/a / 62.9 |

Baseline page/filter timings are `null`: those controls did not exist, and findings beyond the first 100 were inaccessible in its view. Candidate `null` next-page timings mean the workload fits one page. Full raw observations also include first-selection and filtering times, mounted rows and marks, browser version, generation exit codes, artifact hashes and final DOM counts. A candidate switch has the same user intent but different work: baseline mounts the entire text, while candidate mounts one page. These are end-user task observations, not equal-output microbenchmarks.

## Findings and limitations

Maximum ambiguity HTML shrank from 27,340,535 to 4,278,369 bytes (84.4% smaller). The alternating-span workload's selected DOM shrank from 65,611 to 2,102 elements. The ordinary report grew from 17,154 to 21,643 bytes (26.2% larger) because navigation and transport-decoding code add fixed overhead.

Observed median generation time increased for: boundary_alternating, ordinary. Observed median peak generation RSS increased for: none of the frozen workloads. Observed median browser load time increased for: hostile, ordinary. Observed median first-selection time increased for: ambiguity, hostile, page_edges. Observed median candidate-switch time increased for: ambiguity, ordinary, unicode. Small timing differences should be interpreted with the raw samples and shared-host noise, not as stable speed guarantees.

Recovery is still conditional. The ISO ambiguity experiment deliberately fails to recover a unique character, preserves the input and exposes conflicting alternatives. Unsupported Unicode remains unchanged. These negative outcomes are expected and explicitly marked incomplete; pagination does not conceal them or turn them into successful recovery.

The application retains full text, packed diagnostics and code-point arrays. Python still builds the full analysis before packing; JSON download reconstructs the verbose schema and can exceed 10 MiB. Bounded DOM rendering does **not** imply constant total memory. Browser memory and export latency were not measured. Browser Find searches only mounted pages; page/index controls and full downloads reach the remaining content. Code points and CRLF pairs survive page boundaries, while grapheme clusters may be split visually. Clipboard behavior outside the browser is not controlled.

Validation covers Linux and this Chromium build. Other browsers, screen readers, Windows, network filesystems, power-loss durability and unmodeled keyboard states remain unvalidated. No novelty claim is made for dictionary encoding or pagination.
