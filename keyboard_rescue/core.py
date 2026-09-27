"""Deterministic, code-point-preserving candidate conversion."""
from . import __version__
from .layouts import LAYOUTS, REVISION, mapping

MAX_INPUT_BYTES = 65536
LIMITATIONS = [
    "Candidates are conditional on your layout, geometry and span choices; no language detection is performed.",
    "Rendered text cannot always reveal the original keystrokes. Fully mapped does not mean proven recovery.",
    "Only pinned XKB US QWERTY, Dvorak and Colemak base/Shift levels are modeled, with Caps Lock off.",
    "Caps Lock, dead keys, compose, AltGr, Ctrl/Alt/Meta, keypad, remaps and platform-specific behavior are excluded.",
    "Space, tab, CR and LF are preserved as text separators; their key and modifier history is not inferred.",
    "Unsupported and conflicting ambiguous characters are preserved. No Unicode normalization is applied.",
    "Mixed-layout text needs explicit spans; a valid-looking character does not prove which layout produced it.",
    "Offsets and spans count Unicode code points, not bytes, graphemes or UTF-16 units; ends are exclusive.",
]


def validate_spans(spans, length):
    if spans is None:
        return [(0, length)]
    if not spans:
        raise ValueError("at least one span is required")
    result = sorted(spans)
    previous = 0
    for start, end in result:
        if not (0 <= start < end <= length) or start < previous:
            raise ValueError("spans must be nonempty, within the text, and nonoverlapping")
        previous = end
    return result


def convert(text, observed, intended, geometry="ansi", spans=None):
    source, target = mapping(observed, geometry), mapping(intended, geometry)
    regions = validate_spans(spans, len(text))
    inverse = {}
    for key, levels in source.items():
        for level, char in enumerate(levels):
            inverse.setdefault(char, []).append((key, level))
    table = {}
    for char, states in inverse.items():
        choices = [{"key": key, "shift": bool(level), "output": target[key][level]}
                   for key, level in states]
        outputs = sorted({choice["output"] for choice in choices})
        table[char] = (outputs[0] if len(outputs) == 1 else char,
                       "ambiguous" if len(outputs) > 1 else "convergent",
                       choices)
    output, diagnostics, changes = [], [], []
    line, column, byte_offset, region = 1, 1, 0, 0
    unresolved = 0
    for index, char in enumerate(text):
        while region < len(regions) and index >= regions[region][1]:
            region += 1
        selected = region < len(regions) and regions[region][0] <= index < regions[region][1]
        replacement = char
        if selected and char not in " \t\r\n":
            entry = table.get(char)
            kind, choices = "unsupported", []
            if entry:
                replacement, kind, choices = entry
            if not entry or len(choices) > 1:
                diagnostics.append({"index": index, "byte_offset": byte_offset,
                                    "line": line, "column": column, "character": char,
                                    "kind": kind, "choices": choices})
                unresolved += kind != "convergent"
        output.append(replacement)
        if replacement != char:
            if changes and changes[-1]["end"] == index:
                changes[-1]["end"] = index + 1
            else:
                changes.append({"start": index, "end": index + 1})
        byte_offset += len(char.encode("utf-8"))
        if char == "\n":
            line, column = line + 1, 1
        else:
            column += 1
    return {"intended_layout": intended, "text": "".join(output),
            "mapping_status": "unresolved" if unresolved else "fully_mapped_under_model",
            "unresolved_characters": unresolved, "diagnostics": diagnostics,
            "changed_spans": changes,
            "changed_characters": sum(s["end"] - s["start"] for s in changes)}


def analyze(text, observed, intended, geometry="ansi", spans=None):
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} UTF-8 bytes")
    if observed not in LAYOUTS or not intended or any(x not in LAYOUTS for x in intended):
        raise ValueError("explicit observed and intended layouts are required")
    if len(set(intended)) != len(intended):
        raise ValueError("intended layouts must be distinct")
    regions = validate_spans(spans, len(text))
    return {"schema_version": "1.0", "tool_version": __version__,
            "layout_revision": REVISION, "original": text, "observed_layout": observed,
            "geometry": geometry, "selected_spans": [{"start": a, "end": b} for a, b in regions],
            "excluded_characters": len(text) - sum(b - a for a, b in regions),
            "limitations": LIMITATIONS.copy(),
            "candidates": [convert(text, observed, x, geometry, spans) for x in intended]}
