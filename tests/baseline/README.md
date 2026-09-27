# Frozen report baseline

These five Python/HTML files are byte-for-byte snapshots from the catalog tree
`5c6a33219db448f37cec25e565fa08161c603ae6`, prior to the compact report change.
The checkout's commit identity differs from the catalog remote commit, but its
complete tree was verified identical before edits. `provenance.json` records
both identities and SHA-256 hashes. This fixture is test/experiment data, not
installed application code. Do not update it to match the candidate.

`tests/test_report.py` verifies the hashes and compares seeded public-schema
outputs. `scripts/report_worker.py` uses this package for paired generation and
browser measurements. The old renderer intentionally exposes only its first
100 findings and mounts all text highlights; it supplies a reproducible baseline,
not the current UI contract. Both renderers use the same pinned mappings.

`tests/report_workloads.py` defines suite v1 recipes, frozen by
`tests/workloads.json`. Maximum cases have exactly 65,536 UTF-8 input bytes.
The paired experiment uses two candidates in supplied order: Colemak, Dvorak.
