# Layout provenance and attribution

Layout data is derived from the xkeyboard-config project, **2.41**, immutable commit
`2426c5997e9f76a45df2016d1092bff360712e70` (annotated tag object
`2b507a5df5e5833886421de1f02d244b714758d8`).

- Upstream: https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config
- Exact source: https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config/-/tree/2426c5997e9f76a45df2016d1092bff360712e70
- Original notices: [COPYING](vendor/xkeyboard-config/COPYING), [AUTHORS](vendor/xkeyboard-config/AUTHORS), and comments in each vendored file. Colemak's source credits Shai Coleman (2006).
- Every vendored upstream file is unmodified and SHA-256 recorded in [PROVENANCE.json](vendor/xkeyboard-config/PROVENANCE.json). This is a small dependency subset, not the entire upstream distribution. The compiled variants are `pc+us(basic)`, `pc+us(dvorak)` and `pc+us(colemak)` with `evdev` keycodes, complete types and complete compatibility definitions. No host include paths are searched.
- `keyboard_rescue/layouts.py` manually transcribes the first two levels in physical row order. Those derived tables retain the upstream notices; `keyboard_rescue/XKB-COPYING` is an identical copy of upstream COPYING distributed with the installed package.

## Physical keys and modifiers

ANSI supports **TLDE; AE01–AE12; AD01–AD12; BKSL; AC01–AC11; AB01–AB10; SPCE** (48 keys). ISO adds **LSGT** (49 keys). These are XKB physical key names, not characters or language-dependent key labels. This models the printable portion only, not an entire 104/105-key keyboard. Row order and exact outputs are inspectable in the application tables and [oracle fixture](tests/xkb_outputs.json).

The oracle presses no locking or group modifiers. It evaluates each physical key in a fresh keymap/state with a depressed Shift mask of either zero or `1 << xkb_keymap_mod_get_index("Shift")`, and reads `xkb_state_key_get_utf32`. This checks the actual state interpretation, not just a second parser of the symbol lists. Space's two states are checked, although text conversion preserves separators without inferring their modifier history. All higher levels and control-key effects, including Colemak's Caps-to-Backspace behavior, are deliberately outside this model.

## Independent fixture

[tests/xkb_outputs.json](tests/xkb_outputs.json) was generated with:

- `libxkbcommon0 1.6.0-1build1`
- shared-library SHA-256 `3eb6c7315985803a7c72cb81aa3293b763e6cfc907b70b7b2f641c2827cd90f9`
- 3 layouts × 49 keys × 2 states = **294 outputs**

The fixture records the revision, library identity and every output. `python3 scripts/xkb_oracle.py` recompiles the **pinned** data locally and requires every output to match the fixture. It prints the current library identity; another installed version may be used only if it produces exactly the same outputs. To intentionally regenerate the fixture after review, use `--record`. This process never changes the application's manually transcribed tables. The native library is a verification dependency, not an application dependency.

The original upstream source subset and notices can be independently retrieved from the immutable URLs above. `scripts/xkb_oracle.py` validates all source hashes before compiling. No downloads occur during verification.

## Other dependencies

Browser tests use Playwright 1.63.0 (Apache-2.0, as distributed by Microsoft) and its downloaded Chromium build. Exact npm package integrity is in `package-lock.json`; dependency binaries and `node_modules` are not committed or shipped in the application. No external browser scripts, fonts or styles are included in generated reports.

## BoolQ comprehension experiment

`experiments/comprehension/inputs.json` and the BoolQ passages/questions retained
or transformed in `results/comprehension/` come from **BoolQ**, by Christopher
Clark, Kenton Lee, Ming-Wei Chang, Tom Kwiatkowski, Michael Collins and Kristina
Toutanova (2019), [authors' repository](https://github.com/google-research-datasets/boolean-questions),
[paper](https://arxiv.org/abs/1905.10044). They are licensed under
[Creative Commons Attribution-ShareAlike 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
The upstream validation split is mirrored at pinned revision
`35b264d03638db9f4ce671b711558bf7ff0f80d5` of `google/boolq` on Hugging Face.
Selection and keyboard-layout adaptations are described in
[the experiment protocol](experiments/comprehension/README.md). These dataset
materials retain CC BY-SA 3.0; the application MIT license does not replace it.
The model and inference binary are downloaded separately, not redistributed.
