"""Bounded UTF-8 input and exclusive, atomic single-artifact exports."""
import argparse
import os
from pathlib import Path
import signal
import sys
import tempfile
from . import __version__
from .core import MAX_INPUT_BYTES, analyze
from .layouts import LAYOUTS
from .report import html_text, json_text


def span_argument(value):
    try:
        a, b = value.split(":")
        return int(a), int(b)
    except ValueError as error:
        raise argparse.ArgumentTypeError("span must be START:END code-point indices") from error


def read_input(path):
    if path == "-":
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        with open(path, "rb") as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} bytes; split it into smaller files")
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError(f"invalid UTF-8 at byte {error.start}; input was not modified") from error


def atomic_export(destination, data):
    """No overwrite, including symlinks. The final name appears only after fsync.

    POSIX hard linking is required. SIGKILL can leave a hidden .partial file,
    but never exposes an incomplete final file. No non-atomic fallback.
    """
    destination = Path(destination)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".partial",
                                             dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        os.unlink(temporary)


def parser():
    result = argparse.ArgumentParser(description="Recover candidate text under explicit physical-key layout assumptions.")
    result.add_argument("input", nargs="?", default="-", help="UTF-8 file, or - for stdin (max 65536 bytes)")
    result.add_argument("--observed", required=True, choices=LAYOUTS, help="layout that produced the input")
    result.add_argument("--intended", required=True, choices=LAYOUTS, action="append", help="intended layout; repeat for JSON/HTML comparison")
    result.add_argument("--geometry", choices=("ansi", "iso"), default="ansi", help="ISO includes the extra LSGT key (default: ansi)")
    result.add_argument("--span", action="append", type=span_argument, help="convert only START:END code points; repeat for mixed text")
    result.add_argument("--format", choices=("text", "json", "html"), default="text")
    result.add_argument("--output", "-o", help="create a new file; existing files/symlinks are never overwritten")
    result.add_argument("--version", action="version", version=__version__)
    return result


def run(args):
    if args.format == "text" and len(args.intended) != 1:
        raise ValueError("text output requires exactly one intended layout")
    text = read_input(args.input)
    report = analyze(text, args.observed, args.intended, args.geometry, args.span)
    if args.format == "text":
        payload = report["candidates"][0]["text"]
    else:
        payload = (json_text if args.format == "json" else html_text)(report)
    data = payload.encode("utf-8")
    if args.output:
        atomic_export(args.output, data)
    else:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    unresolved = sum(x["unresolved_characters"] for x in report["candidates"])
    findings = sum(len(x["diagnostics"]) for x in report["candidates"])
    print(f"Conditional candidates only. {findings} findings; {unresolved} unresolved characters across candidates."
          + (" Inspect --format json or html for positions and alternatives." if findings else ""), file=sys.stderr)
    return 3 if unresolved else 0


def main(argv=None):
    args = parser().parse_args(argv)
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        return run(args)
    except KeyboardInterrupt:
        print("keyboard-rescue: interrupted; no partial final export is published", file=sys.stderr)
        return 130
    except BrokenPipeError:
        # Avoid another flush failure at interpreter shutdown.
        sys.stdout = open(os.devnull, "w")
        return 2
    except (OSError, ValueError) as error:
        print(f"keyboard-rescue: {error}", file=sys.stderr)
        return 2
    finally:
        signal.signal(signal.SIGTERM, previous)
