#!/usr/bin/env python3
"""Generate independent key outputs from vendored XKB sources using libxkbcommon.

No application imports. No system XKB include paths. No network.
"""
import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor/xkeyboard-config"
FIXTURE = ROOT / "tests/xkb_outputs.json"


def check_sources():
    provenance = json.loads((VENDOR / "PROVENANCE.json").read_text())
    for name, digest in provenance["sha256"].items():
        actual = hashlib.sha256((VENDOR / name).read_bytes()).hexdigest()
        if actual != digest:
            raise AssertionError(f"source hash mismatch: {name}")
    return provenance


def generate():
    provenance = check_sources()
    library = ctypes.util.find_library("xkbcommon")
    if not library:
        raise RuntimeError("libxkbcommon is required for independent verification")
    lib = C.CDLL(library)
    def bind(name, result, *arguments):
        function = getattr(lib, name)
        function.restype, function.argtypes = result, arguments
        return function
    ptr, u32, string = C.c_void_p, C.c_uint32, C.c_char_p
    new_context = bind("xkb_context_new", ptr, C.c_int)
    add_path = bind("xkb_context_include_path_append", C.c_int, ptr, string)
    new_keymap = bind("xkb_keymap_new_from_string", ptr, ptr, string, C.c_int, C.c_int)
    key_by_name = bind("xkb_keymap_key_by_name", u32, ptr, string)
    mod_index = bind("xkb_keymap_mod_get_index", u32, ptr, string)
    new_state = bind("xkb_state_new", ptr, ptr)
    update_mask = bind("xkb_state_update_mask", C.c_int, ptr, u32, u32, u32, u32, u32, u32)
    get_char = bind("xkb_state_key_get_utf32", u32, ptr, u32)
    free_state = bind("xkb_state_unref", None, ptr)
    free_keymap = bind("xkb_keymap_unref", None, ptr)
    free_context = bind("xkb_context_unref", None, ptr)
    context = new_context(1 | 2)  # NO_DEFAULT_INCLUDES | NO_ENVIRONMENT_NAMES
    assert context and add_path(context, str(VENDOR).encode())
    keys = ["TLDE"] + [f"AE{i:02}" for i in range(1, 13)]
    keys += [f"AD{i:02}" for i in range(1, 13)] + ["BKSL"]
    keys += [f"AC{i:02}" for i in range(1, 12)] + [f"AB{i:02}" for i in range(1, 11)]
    keys += ["SPCE", "LSGT"]
    layouts = {}
    try:
        for name, variant in (("qwerty", "basic"), ("dvorak", "dvorak"), ("colemak", "colemak")):
            source = ('xkb_keymap { xkb_keycodes { include "evdev" }; '
                      'xkb_types { include "complete" }; '
                      'xkb_compatibility { include "complete" }; '
                      f'xkb_symbols {{ include "pc+us({variant})" }}; }};')
            keymap = new_keymap(context, source.encode(), 1, 0)
            assert keymap, f"could not compile {name}"
            state = new_state(keymap)
            assert state
            try:
                shift = mod_index(keymap, b"Shift")
                assert shift < 32
                rows = {}
                for key in keys:
                    code = key_by_name(keymap, key.encode())
                    assert code != 0xffffffff
                    values = []
                    for level in (0, 1):
                        update_mask(state, (1 << shift) if level else 0, 0, 0, 0, 0, 0)
                        value = get_char(state, code)
                        assert value > 0, (name, key, level)
                        values.append(chr(value))
                    rows[key] = values
                layouts[name] = rows
            finally:
                free_state(state)
                free_keymap(keymap)
    finally:
        free_context(context)
    return {"revision": provenance["revision"], "outputs": layouts}


def library_metadata():
    result = {"soname": ctypes.util.find_library("xkbcommon")}
    # Linux provenance; output equivalence is still checked on other platforms.
    try:
        result["package"] = subprocess.check_output(
            ["dpkg-query", "-W", "-f=${Package} ${Version}", "libxkbcommon0"], text=True)
        paths = [line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                 if 'libxkbcommon.so' in line]
        if paths:
            result['sha256'] = hashlib.sha256(Path(paths[0]).read_bytes()).hexdigest()
    except (OSError, subprocess.CalledProcessError):
        result['package'] = 'unavailable'
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true", help="intentionally replace fixture after review")
    args = parser.parse_args()
    generated = generate()
    if args.record:
        generated["generator"] = library_metadata()
        FIXTURE.write_text(json.dumps(generated, sort_keys=True, indent=2) + "\n")
    else:
        expected = json.loads(FIXTURE.read_text())
        assert generated["revision"] == expected["revision"]
        assert generated["outputs"] == expected["outputs"], "libxkbcommon output differs from pinned fixture"
    print(f"Verified {sum(len(x)*2 for x in generated['outputs'].values())} key/modifier outputs against vendored XKB sources.")
    print(json.dumps(library_metadata(), sort_keys=True))
