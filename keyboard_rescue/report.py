"""A standalone report: data never enters an HTML or JavaScript code context."""
import base64
import hashlib
import json
from pathlib import Path


def json_text(report):
    return json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"


def compact_report(report):
    """Lossless HTML transport, independent of the public JSON schema.

    Store repeated diagnostic descriptions once, and positions as integer tuples.
    Copy containers rather than mutating the caller's analysis.
    """
    types, lookup, candidates = [], {}, []
    for candidate in report["candidates"]:
        rows = []
        for diagnostic in candidate["diagnostics"]:
            description = [diagnostic["character"], diagnostic["kind"], diagnostic["choices"]]
            key = (diagnostic["character"], diagnostic["kind"],
                   tuple((c["key"], c["shift"], c["output"]) for c in diagnostic["choices"]))
            if key not in lookup:
                lookup[key] = len(types)
                types.append(description)
            rows.append([diagnostic[k] for k in ("index", "byte_offset", "line", "column")] + [lookup[key]])
        candidates.append({**candidate, "diagnostics": rows,
                           "changed_spans": [[s["start"], s["end"]] for s in candidate["changed_spans"]]})
    return {"html_format": 1, "diagnostic_types": types,
            "report": {**report, "candidates": candidates}}


def html_text(report):
    template = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    data = json_text(compact_report(report)).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    # Hash only the executable script. User data is inert JSON with escaped '<'.
    script = template.split('<script id="app">', 1)[1].split("</script>", 1)[0]
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    return template.replace("__SCRIPT_HASH__", digest).replace("__REPORT_DATA__", data)
