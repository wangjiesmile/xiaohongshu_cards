#!/usr/bin/env python3
"""Inspect Markdown structure and image references without altering the source."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from common import InputError, write_json


HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")


def inspect(source: Path) -> dict[str, object]:
    try:
        text = source.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InputError(f"Markdown 不存在: {source}") from exc
    if not text.strip():
        raise InputError("Markdown 不能为空")
    headings: list[dict[str, object]] = []
    images: list[dict[str, object]] = []
    fenced = False
    paragraph_count = 0
    in_paragraph = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```") or line.lstrip().startswith("~~~"):
            fenced = not fenced
            in_paragraph = False
            continue
        if fenced:
            continue
        heading = HEADING.match(line)
        if heading:
            headings.append(
                {
                    "level": len(heading.group(1)),
                    "text": heading.group(2).strip(),
                    "line": line_number,
                }
            )
            in_paragraph = False
        else:
            stripped = line.strip()
            if stripped and not stripped.startswith((">", "- ", "* ", "+ ")):
                if not in_paragraph:
                    paragraph_count += 1
                in_paragraph = True
            else:
                in_paragraph = False
        for alt, target in IMAGE.findall(line):
            images.append(
                {
                    "index": len(images) + 1,
                    "alt": alt.strip(),
                    "source": target.strip("<>"),
                    "line": line_number,
                }
            )
    title = next((str(h["text"]) for h in headings if h["level"] == 1), source.stem)
    return {
        "version": 1,
        "source": str(source.resolve()),
        "title": title,
        "headings": headings,
        "images": images,
        "paragraph_count": paragraph_count,
        "character_count": len(text),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        source = Path(args.source).expanduser().resolve()
        result = inspect(source)
        write_json(Path(args.output).expanduser().resolve(), result)
        print(args.output)
        return 0
    except (InputError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
