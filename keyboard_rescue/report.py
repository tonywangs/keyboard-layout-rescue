"""A standalone report: data never enters an HTML or JavaScript code context."""
import base64
import hashlib
import json
from pathlib import Path


def json_text(report):
    return json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"


def html_text(report):
    template = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    data = json_text(report).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    # Hash only the executable script. User data is inert JSON with escaped '<'.
    script = template.split('<script id="app">', 1)[1].split("</script>", 1)[0]
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    return template.replace("__SCRIPT_HASH__", digest).replace("__REPORT_DATA__", data)
