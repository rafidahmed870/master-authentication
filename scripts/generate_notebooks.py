#!/usr/bin/env python3
"""
generate_notebooks.py
=====================
Converts Markdown documentation files (.md) in the docs/ directory into
Jupyter Notebook files (.ipynb) in the notebooks/ directory.

Each Markdown file produces one notebook.

Conversion rules:
  - Fenced code blocks (``` ... ```) become executable Code cells.
    The language hint on the opening fence is preserved as cell metadata.
  - Everything else (headings, prose, lists, tables, Mermaid blocks)
    becomes Markdown cells.
  - Consecutive non-code lines are merged into a single Markdown cell.
  - Empty lines between prose sections do NOT create new cells unless a
    code block boundary is crossed.

Usage:
  # From the repository root:
  python scripts/generate_notebooks.py

  # Convert a single file:
  python scripts/generate_notebooks.py --file docs/01_Role_Based_Access_Control.md

  # Specify custom input/output directories:
  python scripts/generate_notebooks.py --docs-dir docs --notebooks-dir notebooks

Requirements:
  Python >= 3.8  (no third-party packages required)

Note:
  The generated notebooks are intended for reading and learning, not for
  executing production code. Code cells contain illustrative pseudocode or
  TypeScript examples that require a compatible kernel to run.

AI-generated content notice:
  The source Markdown files were produced with the assistance of an AI
  language model. AI can make mistakes. Review content critically before
  applying it to production systems.
"""

import argparse
import json
import re
import sys
import uuid
from pathlib import Path


# ---------------------------------------------------------------------------
# Notebook skeleton
# ---------------------------------------------------------------------------

def new_notebook(title: str) -> dict:
    """Return a minimal nbformat v4 notebook skeleton."""
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.8.0",
            },
            "title": title,
        },
        "cells": [],
    }


def markdown_cell(source: str) -> dict:
    """Return an nbformat v4 Markdown cell."""
    return {
        "cell_type": "markdown",
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": source.rstrip("\n"),
    }


def code_cell(source: str, language: str = "") -> dict:
    """Return an nbformat v4 code cell."""
    cell: dict = {
        "cell_type": "code",
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": source.rstrip("\n"),
        "outputs": [],
        "execution_count": None,
    }
    if language:
        cell["metadata"]["language"] = language
    return cell


# ---------------------------------------------------------------------------
# Markdown → cells parser
# ---------------------------------------------------------------------------

# Matches the opening fence of a code block, capturing the optional language.
# Supports ``` and ~~~
_FENCE_OPEN  = re.compile(r"^(`{3,}|~{3,})\s*(\w*).*$")
_FENCE_CLOSE = re.compile(r"^(`{3,}|~{3,})\s*$")


def parse_cells(md_text: str) -> list:
    """
    Parse a Markdown string into a list of notebook cell dicts.

    The parser walks the file line by line and maintains a small state
    machine:
      - PROSE  : accumulating lines for a Markdown cell
      - CODE   : inside a fenced code block, accumulating lines for a Code cell
    """
    cells = []
    lines = md_text.splitlines(keepends=True)

    state = "PROSE"
    current_lines: list[str] = []
    current_lang = ""
    fence_marker = ""   # the actual fence chars used to open the block

    def flush_prose():
        nonlocal current_lines
        text = "".join(current_lines).strip()
        if text:
            cells.append(markdown_cell(text))
        current_lines = []

    def flush_code():
        nonlocal current_lines, current_lang
        text = "".join(current_lines)
        if text.strip():
            cells.append(code_cell(text, current_lang))
        current_lines = []
        current_lang = ""

    for line in lines:
        stripped = line.rstrip("\n")

        if state == "PROSE":
            m = _FENCE_OPEN.match(stripped)
            if m:
                # Entering a code block
                flush_prose()
                fence_marker = m.group(1)[0] * len(m.group(1))  # normalise
                current_lang = m.group(2).lower()
                state = "CODE"
            else:
                current_lines.append(line)

        elif state == "CODE":
            # Check for closing fence (same or longer marker of same char)
            close_m = _FENCE_CLOSE.match(stripped)
            if close_m and stripped[0] == fence_marker[0] and len(stripped.rstrip()) >= len(fence_marker):
                flush_code()
                state = "PROSE"
                fence_marker = ""
            else:
                current_lines.append(line)

    # Flush whatever is left
    if state == "PROSE":
        flush_prose()
    elif state == "CODE":
        # Unclosed fence — treat accumulated lines as a code cell anyway
        flush_code()

    return cells


# ---------------------------------------------------------------------------
# File-level conversion
# ---------------------------------------------------------------------------

def md_to_notebook(md_path: Path) -> dict:
    """Convert a single Markdown file to a notebook dict."""
    text = md_path.read_text(encoding="utf-8")

    # Derive a human-readable title from the filename
    title = md_path.stem.replace("_", " ")

    nb = new_notebook(title)
    nb["cells"] = parse_cells(text)
    return nb


def write_notebook(nb: dict, out_path: Path) -> None:
    """Serialise a notebook dict to a .ipynb file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(nb, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert docs/*.md files to notebooks/*.ipynb files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--docs-dir",
        type=Path,
        default=None,
        help="Directory containing .md source files. "
             "Defaults to <repo_root>/docs",
    )
    p.add_argument(
        "--notebooks-dir",
        type=Path,
        default=None,
        help="Output directory for .ipynb files. "
             "Defaults to <repo_root>/notebooks",
    )
    p.add_argument(
        "--file",
        type=Path,
        default=None,
        metavar="MD_FILE",
        help="Convert a single Markdown file instead of the whole docs/ dir.",
    )
    return p


def resolve_repo_root(script_path: Path) -> Path:
    """
    Infer the repository root from the script location.
    Expected layout:  <repo_root>/scripts/generate_notebooks.py
    """
    return script_path.resolve().parent.parent


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    repo_root = resolve_repo_root(Path(__file__))

    docs_dir      = args.docs_dir      or repo_root / "docs"
    notebooks_dir = args.notebooks_dir or repo_root / "notebooks"

    # Single-file mode
    if args.file:
        md_file = args.file.resolve()
        if not md_file.exists():
            print(f"ERROR: file not found: {md_file}", file=sys.stderr)
            return 1
        out_file = notebooks_dir / md_file.with_suffix(".ipynb").name
        nb = md_to_notebook(md_file)
        write_notebook(nb, out_file)
        print(f"  {md_file.name}  →  {out_file.relative_to(repo_root)}")
        return 0

    # Batch mode — convert all .md files in docs_dir
    if not docs_dir.is_dir():
        print(f"ERROR: docs directory not found: {docs_dir}", file=sys.stderr)
        return 1

    md_files = sorted(docs_dir.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {docs_dir}", file=sys.stderr)
        return 1

    print(f"Source  : {docs_dir}")
    print(f"Output  : {notebooks_dir}")
    print()

    converted = 0
    for md_file in md_files:
        out_file = notebooks_dir / md_file.with_suffix(".ipynb").name
        nb = md_to_notebook(md_file)
        write_notebook(nb, out_file)
        cell_count = len(nb["cells"])
        code_cells = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
        print(
            f"  {md_file.name:<45}  →  {out_file.name}"
            f"  ({cell_count} cells, {code_cells} code)"
        )
        converted += 1

    print()
    print(f"Done. {converted} notebook(s) written to {notebooks_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
