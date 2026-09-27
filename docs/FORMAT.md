# JSON contract, schema 1.0

JSON is UTF-8, compact, ASCII-escaped, sorted by object key and terminated by one LF. It contains no clock time, input path, random identifier or host-specific value. Identical text and options under the same tool version produce byte-identical JSON and HTML. Candidate order follows the supplied `--intended` options. Layout choices cannot repeat.

The top-level object contains:

| Field | Meaning |
| --- | --- |
| `schema_version` | `"1.0"`; change when the contract changes incompatibly |
| `tool_version` | Application version, currently `"1.0.0"` |
| `layout_revision` | Full immutable xkeyboard-config commit |
| `original` | Exact decoded input, before any conversion |
| `observed_layout` | `qwerty`, `dvorak` or `colemak` |
| `geometry` | `ansi` or `iso` |
| `selected_spans` | Sorted `{start, end}` code-point intervals; implicit full span if unspecified |
| `excluded_characters` | Code points outside those intervals; unexamined |
| `limitations` | Human-readable model assumptions and exclusions |
| `candidates` | One to three explicit intended-layout results |

Each candidate contains `intended_layout`, `text`, `mapping_status`, `unresolved_characters`, `changed_characters`, `changed_spans`, and `diagnostics`.

- `mapping_status` is `fully_mapped_under_model` or `unresolved`. The former describes only selected characters under the stated assumptions, not proven historical recovery.
- `changed_spans` is a sorted list of maximal contiguous `{start, end}` intervals where the original and candidate differ. It may join adjacent selected regions. Since all modeled outputs are single code points, source and target offsets coincide.
- `diagnostics` are sorted by original position. Each contains zero-based `index` (code points), zero-based `byte_offset` (UTF-8), one-based `line` and `column`, the original single-code-point `character`, `kind`, and a `choices` array.
- Each choice is `{key, shift, output}`. `key` is the XKB key name; `shift` is a boolean; `output` is the character from that target key state. Choice order follows physical row order, then base before Shift, with LSGT last.
- `unsupported`: no source state fits; `choices` is empty and text is preserved.
- `ambiguous`: multiple source states fit and give different target characters; all choices are shown and text is preserved.
- `convergent`: multiple source states fit but all give the same target character; that agreed output is used. Keystroke information is still ambiguous, so the diagnostic is retained.

`unresolved_characters` counts `unsupported` and `ambiguous` findings, not convergent findings. Space, tab, CR and LF pass through without per-character diagnostics; their lack of key-history inference is stated globally. No diagnostics are emitted outside the selected spans. The empty input has implicit span `{start: 0, end: 0}`; explicit empty spans are invalid.

Columns count Unicode code points, not grapheme clusters, visual columns, bytes or JavaScript UTF-16 units. Only LF advances a line. Tabs count as one column and CR is preserved without incrementing the line. Surrogate code points are not valid UTF-8 input. NUL, a BOM, bidi controls and combining marks are preserved with unsupported diagnostics when selected. The browser uses `Array.from(text)` to apply code-point offsets, avoiding UTF-16 offset errors on supplementary characters.

HTML embeds the same report with `<`, `>` and `&` additionally JSON-escaped. A fixed, hashed script parses that inert data and uses DOM text nodes, not HTML insertion. Its full-analysis download is semantically identical JSON; those additional escapes remain, so its bytes can differ from the direct JSON export. The report has no preselected candidate and performs no re-analysis or network requests in the browser.
