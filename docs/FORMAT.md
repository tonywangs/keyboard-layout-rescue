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

## Compact HTML transport (version 1)

The public JSON contract above is unchanged. HTML embeds an internal transport object:

```text
{html_format: 1, diagnostic_types: [...], report: {...}}
```

`report` preserves all top-level metadata, original text, candidate text and counts. Within each candidate, `changed_spans` becomes a list of `[start, end]` pairs. Each diagnostic becomes `[index, byte_offset, line, column, type_id]`. `diagnostic_types[type_id]` is `[character, kind, choices]`, with each choice retaining its public `{key, shift, output}` structure. Types are deduplicated across all candidates in first-occurrence order. Positions are absolute, so each row can be decoded independently. This is a lossless dictionary representation, not compression requiring a codec or network dependency. It is distinct from schema 1.0 and must not be consumed as a public analysis JSON file.

The script reconstructs public diagnostic objects only for mounted rows or full JSON download. It retains the entire packed dataset, full text and code-point arrays in memory. Generation still creates the full Python analysis before packing. Total memory therefore grows with input; only the text and diagnostic views have fixed rendering bounds.

`<`, `>` and `&` are JSON-escaped in the embedded transport. A fixed, CSP-hashed script reads inert JSON and inserts text nodes, never imported HTML. The full-analysis download reconstructs the original schema with all diagnostics and alternatives. It is semantically identical to direct JSON output, although key ordering and escapes differ. All text downloads use complete strings and UTF-8; no page slice, newline normalization or BOM is added. Clipboard writes also receive the complete string; OS clipboard behavior beyond the browser is not controlled. If clipboard access fails, focus moves to the full-download button and a status message explains the fallback.

## Pagination and positions

Text pages contain at most 2,000 Unicode code points. A boundary between CR and LF is moved back by one code point, keeping CRLF together. Original and candidate share page boundaries because conversion preserves code-point counts. Changed spans are clipped to the visible interval without altering the stored spans. Supplementary Unicode characters are never split into surrogate halves. Grapheme clusters (for example a letter followed by a combining mark) may cross pages. The browser's native Find searches mounted text only, so use page controls, code-point index navigation, or download full text for whole-document searching.

Diagnostic pages mount at most 100 rows (below the 500-row ceiling). Type filters retain original order and expose counts of matching and total findings. All pages have previous/next controls and a labeled direct page input. Diagnostic position buttons jump to the corresponding text page and focus the candidate pane. Text index input accepts zero-based code-point indices; invalid page and index submissions are rejected by native form constraints. Result counts and page changes are announced through polite status regions. Selection remains explicit; no radio is checked initially. Page and filter state never affects full exports.

These use native buttons, labeled controls, visible focus and status regions, informed by [W3C status-message guidance](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html). Code-point arrays use the string iterator through [Array.from](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/from). Automated Chromium keyboard checks are not a screen-reader audit or a claim of WCAG conformance.
