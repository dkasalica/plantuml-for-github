"""
template.py -- generate Chrome/* and Firefox/* files from template/*
using a minimal built-in preprocessor (no external dependency).

For every file found in `template/`, this script runs the preprocessor
twice: once with CHROME defined (writing to Chrome/<filename>) and once
with FIREFOX defined (writing to Firefox/<filename>), overwriting any
existing file. The template files use these directives:

    #if TOKEN
        ... lines kept only when TOKEN is defined ...
    #endif

Only `#if <single token>` and `#endif` are recognized. No `#else`,
no `#elif`, no nested `#if`, no expressions, no macros. Anything more
exotic is intentionally not supported -- keep templates simple.

JSON syntax is validated for .json outputs (fail fast on template bugs).
"""

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths (resolved relative to this script's location so it works regardless
# of the current working directory).
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "template"

TARGETS = {
    "CHROME":  ROOT / "Chrome",
    "FIREFOX": ROOT / "Firefox",
}

# Match `#if TOKEN` and `#endif`, allowing leading whitespace and a
# trailing comment after the token (anything after the token is ignored).
_IF_RE    = re.compile(r"^\s*#if\s+(\S+)\s*.*$")
_ENDIF_RE = re.compile(r"^\s*#endif\s*.*$")


def preprocess(source_text: str, define: str, source_path: Path) -> str:
    """
    Strip `#if TOKEN` / `#endif` blocks from `source_text`. Lines inside
    a `#if TOKEN` block are kept iff TOKEN == define; the directive
    lines themselves (`#if ...` and `#endif`) are always removed.

    Raises SystemExit on malformed templates (unmatched #if/#endif,
    nested #if).
    """
    out = []
    keeping = True       # are we currently emitting lines?
    in_if = False        # are we inside a #if block?
    if_line_no = 0       # line number of the open #if, for error messages

    for lineno, line in enumerate(source_text.splitlines(keepends=True), start=1):
        m_if = _IF_RE.match(line)
        m_endif = _ENDIF_RE.match(line)

        if m_if:
            if in_if:
                _die(source_path, lineno,
                     f"nested #if not supported (previous #if on line {if_line_no})")
            in_if = True
            if_line_no = lineno
            token = m_if.group(1)
            keeping = (token == define)
            # Directive line itself is dropped.
            continue

        if m_endif:
            if not in_if:
                _die(source_path, lineno, "#endif without matching #if")
            in_if = False
            keeping = True
            continue

        if keeping:
            out.append(line)

    if in_if:
        _die(source_path, if_line_no, "#if without matching #endif")

    return "".join(out)


def _die(source_path: Path, lineno: int, message: str) -> None:
    sys.stderr.write(f"ERROR: {source_path}:{lineno}: {message}\n")
    sys.exit(2)


def validate(processed: str, output_path: Path, define: str) -> None:
    """
    Per-extension sanity checks. Currently only validates JSON syntax
    for .json files; other file types are written as-is.
    """
    if output_path.suffix.lower() == ".json":
        try:
            json.loads(processed)
        except json.JSONDecodeError as exc:
            sys.stderr.write(
                f"ERROR: preprocessed output for {define} {output_path.name} "
                f"is not valid JSON: {exc}\n"
                f"--- output that failed to parse ---\n"
                f"{processed}\n"
                f"--- end ---\n"
            )
            sys.exit(2)


def build_one(define: str, source_path: Path, output_path: Path) -> None:
    """
    Preprocess one template file for the given `define` and write the
    result to `output_path` (overwriting).
    """
    source_text = source_path.read_text(encoding="utf-8")
    processed = preprocess(source_text, define, source_path)
    validate(processed, output_path, define)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(processed, encoding="utf-8", newline="\n")
    print(f"  wrote {output_path.relative_to(ROOT)} ({len(processed)} bytes)")


def main() -> None:
    if not TEMPLATE_DIR.is_dir():
        sys.stderr.write(f"ERROR: template directory not found: {TEMPLATE_DIR}\n")
        sys.exit(1)

    # Find every regular file inside template/ (recursively).
    template_files = sorted(
        p for p in TEMPLATE_DIR.rglob("*") if p.is_file()
    )
    if not template_files:
        sys.stderr.write(f"ERROR: no files found in {TEMPLATE_DIR}\n")
        sys.exit(1)

    print(f"Generating from {TEMPLATE_DIR.relative_to(ROOT)}/ "
          f"({len(template_files)} file(s))")
    for define, output_dir in TARGETS.items():
        print(f"[{define}] -> {output_dir.relative_to(ROOT)}/")
        for source_path in template_files:
            # Preserve subdirectory structure under the target dir.
            rel = source_path.relative_to(TEMPLATE_DIR)
            output_path = output_dir / rel
            build_one(define, source_path, output_path)
    print("Done.")


if __name__ == "__main__":
    main()
