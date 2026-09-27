# Keyboard Layout Rescue

Recover a **candidate** for text typed under the wrong keyboard layout, entirely offline. Supply the layout that produced the text and the one you meant to use. The tool preserves physical key positions and base/Shift levels for pinned **US QWERTY, Dvorak, and Colemak** mappings.

```text
Observed US QWERTY:  hkuu; w;sug
Intended Colemak:    hello world
```

The CLI reads UTF-8 files or stdin and produces plain text, deterministic JSON, or a self-contained HTML comparison. The report starts with **no candidate selected**, highlights changed spans, explains uncertain positions, and lets you copy or download your explicit choice. It makes no network requests and needs no server.

Rendered text cannot always reveal the original keystrokes. This is a conditional conversion tool, not automatic language detection or proof of recovery. Unsupported characters and conflicting inverse mappings remain unchanged and receive diagnostics.

## Install and run offline

Requires Python 3.10+ on POSIX (validated on Linux with Python 3.12). There are no runtime Python dependencies. From this checkout, install into a **new** directory:

```sh
python3 scripts/install.py .venv
.venv/bin/keyboard-rescue --version
printf 'hkuu; w;sug' | .venv/bin/keyboard-rescue --observed qwerty --intended colemak
```

The installer creates an isolated environment without pip or downloads; it refuses an existing destination. It supports paths containing spaces. You can run the installed command from another directory. To uninstall, remove the environment you created. For environments with a Python packaging toolchain already available, the project also includes standard `pyproject.toml` metadata; the tested installation route is the offline installer above.

For a quick run without installing, use `python3 -m keyboard_rescue` from the checkout.

```sh
# A new text file; the original is read-only and no existing file is overwritten.
.venv/bin/keyboard-rescue examples/wrong-colemak.txt \
  --observed qwerty --intended colemak --output recovered.txt

# Compare two explicit possibilities; open comparison.html in your browser.
.venv/bin/keyboard-rescue examples/wrong-colemak.txt \
  --observed qwerty --intended colemak --intended dvorak \
  --format html --output comparison.html

# Machine-readable analysis, with the original text, changes and diagnostics.
.venv/bin/keyboard-rescue examples/wrong-colemak.txt \
  --observed qwerty --intended colemak --format json
```

`--observed` means the layout that **produced the visible characters**, not the layout you wanted. Reversing it changes the answer. Plain text output requires exactly one `--intended`; repeat that option for JSON or HTML.

## Uncertainty and mixed text

The default `--geometry ansi` models 48 printable physical keys, including Space. `--geometry iso` adds the physical `LSGT` key between left Shift and the usual Z position. Choose the geometry you actually used. ISO provides a concrete inverse ambiguity:

```sh
printf '<>' | .venv/bin/keyboard-rescue \
  --observed qwerty --intended dvorak --geometry iso --format json
```

The first `<` could have come from Shift+AB08, which becomes `W` in Dvorak, or base LSGT, which stays `<`. The tool preserves `<` and reports both choices. This command produces a valid report and exits **3** because there are unresolved positions. If multiple possible key states agree on the target character, the agreed output is used and a `convergent` diagnostic still records the lost keystroke information.

For text containing both correct and mistyped sections, select only the mistaken spans:

```sh
printf 'Keep this: hkuu; w;sug.' | .venv/bin/keyboard-rescue \
  --observed qwerty --intended colemak --span 11:22
# Keep this: hello world.
```

Spans are zero-based Unicode code-point offsets, with an exclusive end. Repeat `--span` for multiple nonoverlapping regions. Outside characters remain unexamined and unchanged; their count is explicit in the report. Without spans, the whole input is analyzed. No heuristic guesses where a layout changed.

## Limits and file handling

- At most **65,536 input bytes**, strict UTF-8. A BOM is retained as an unsupported character; no normalization is performed. Split longer documents before conversion.
- Only base and Shift states, with Caps Lock off. No Caps Lock reconstruction, AltGr, dead keys, compose sequences, Ctrl/Alt/Meta, keypad, platform variants, custom mappings, or edit-history inference. The XKB Colemak Caps-to-Backspace binding is outside the model.
- Space, tab, LF, and CR are retained as separators, including CRLF. Their originating key/modifier states are not inferred. Line numbers advance on LF; columns count code points, including tabs and CR.
- A fully mapped candidate can still be wrong: pasted text, mixed layouts, Caps Lock or another layout may produce the same characters. Unsupported characters outside selected spans are intentionally not diagnosed.
- HTML displays all text and changed spans, but only the first 100 diagnostics for the selected candidate; downloading its **full analysis JSON** retains every diagnostic. Browser text display can conceal NUL, bidi and combining characters; use exact JSON offsets and exports for inspection.
- Output can be much larger than input: a 64 KiB ISO ambiguity case with two candidates produces about 26 MiB of HTML. The input bound limits work but is not an output-size promise. See actual [measurements](results/benchmark.json).
- Exports use a private `0600` temporary file in the destination directory, flush/fsync it, then atomically hard-link it to a **new** final name. Existing files, hardlinks, directories and even dangling symlinks are refused. The filesystem must support hard links; there is no unsafe fallback. File outputs are validated on Linux, not Windows or network filesystems.
- Catchable interrupts and write failures clean up the staged file. SIGKILL or a crash can leave a hidden `.<name>.*.partial` file; it is never an incomplete final report. A signal after publication can leave the **complete** final artifact. Directory-entry durability across power loss is not guaranteed. Stdout is a stream and cannot be rolled back; redirecting with your shell does not have the CLI's atomic-export guarantees.
- Clipboard APIs depend on the browser. If access is denied, the report selects the candidate text and offers an exact UTF-8 download. Report files contain the input text and should be handled accordingly.

Exit codes: **0** = all selected characters mapped under the stated model, **3** = valid output with unresolved positions in at least one candidate, **2** = input/export/usage error, **130** = handled interruption. Summaries go to stderr; stdout stays clean. Convergent diagnostics alone do not trigger exit 3. No exit code asserts recovery of historical keystrokes.

## Verify

The core application is dependency-free. Full verification additionally needs a local `libxkbcommon.so.0`, Node.js 20+, and the pinned Playwright Chromium. Install browser test prerequisites once while online:

```sh
npm ci --ignore-scripts
npx playwright install chromium
```

Then one command runs the full suite **without downloading anything**:

```sh
python3 scripts/verify.py
```

If using a custom browser cache, set `PLAYWRIGHT_BROWSERS_PATH` for both installation and verification. The suite checks vendored source hashes and 294 live libxkbcommon key/modifier outputs, all application mappings, 600 seeded sequences over every directed layout pair in both geometries, failure cleanup, actual SIGTERM handling, six installed offline CLI scenarios, Chromium interaction/security checks with networking blocked, and publication-size limits. Missing browser or native-library prerequisites fail visibly rather than silently skipping checks.

The installed CLI check runs outside the checkout with Python isolated mode and an active socket-denial audit hook. This verifies the runtime needs no network; it is not an OS-level sandbox for arbitrary native code. Browser verification uses Chromium offline mode plus an HTTP(S)-abort route. Python failure-injection tests cover write/fsync/link faults and collisions; they do not simulate hardware power failure.

Actual evidence is in [results/tests.log](results/tests.log) and [results/benchmark.json](results/benchmark.json). Regenerate bounded Linux measurements with:

```sh
python3 scripts/benchmark.py --record results/benchmark.json
```

Measurements launch fresh CLI processes and record elapsed wall time, peak process RSS, artifact sizes and hashes. Inputs, method and every individual repetition are preserved; no browser memory claim is made. `python3 scripts/verify.py --record` refreshes the plain test log.

See [mapping provenance](THIRD_PARTY.md), [the JSON contract](docs/FORMAT.md), and [validation notes](results/README.md).

## Existing work and source data

Layout conversion is established functionality; novelty is not claimed. [Mahou](https://github.com/iamkarlson/Mahou) converts selected or recently typed text through desktop layout-switching workflows. This project has a narrower offline file/report workflow with explicit assumptions and unresolved-character diagnostics; it incorporates no Mahou code.

The mapping authority is [xkeyboard-config 2.41 at commit 2426c599](https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config/-/tree/2426c5997e9f76a45df2016d1092bff360712e70). Independent outputs are produced by [libxkbcommon's state API](https://xkbcommon.org/doc/current/group__state.html), using only the vendored source subset and an explicit `pc+us(variant)` keymap. The application itself does not load host keyboard configuration or libxkbcommon.

Application code is MIT licensed. Third-party layout data retains its original notices and licenses.
