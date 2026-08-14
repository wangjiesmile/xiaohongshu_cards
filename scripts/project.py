#!/usr/bin/env python3
"""Create and confirm the cover stage of a card project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import InputError, read_json, require_text, validate_project, write_json


def create(args: argparse.Namespace) -> None:
    path = Path(args.output).expanduser().resolve()
    data = {
        "version": 1,
        "seriesTitle": require_text(args.series_title, "series-title", limit=80),
        "handle": (args.handle or "").strip()[:80],
        "cover": {
            "title": require_text(args.title, "title", limit=40),
            "illustration": require_text(args.illustration, "illustration", limit=300),
            "status": "draft",
        },
        "cards": [],
    }
    validate_project(data, base=path.parent, allow_empty=True)
    write_json(path, data)
    print(path)


def confirm_cover(args: argparse.Namespace) -> None:
    path = Path(args.project).expanduser().resolve()
    data = read_json(path)
    validate_project(data, base=path.parent, allow_empty=True)
    data["cover"]["status"] = "confirmed"
    write_json(path, data)
    print(path)


def status(args: argparse.Namespace) -> None:
    import json

    path = Path(args.project).expanduser().resolve()
    data = read_json(path)
    project = validate_project(data, base=path.parent, allow_empty=True)
    print(
        json.dumps(
            {
                "cover": project["cover"]["status"],
                "card_count": len(project["pages"]),
                "ready_for_full_render": project["cover"]["status"] == "confirmed" and bool(project["pages"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    item = commands.add_parser("create")
    item.add_argument("--output", required=True)
    item.add_argument("--series-title", required=True)
    item.add_argument("--title", required=True)
    item.add_argument("--illustration", required=True)
    item.add_argument("--handle")
    item.set_defaults(handler=create)
    item = commands.add_parser("confirm-cover")
    item.add_argument("project")
    item.set_defaults(handler=confirm_cover)
    item = commands.add_parser("status")
    item.add_argument("project")
    item.set_defaults(handler=status)
    return result


def main() -> int:
    try:
        args = parser().parse_args()
        args.handler(args)
        return 0
    except (InputError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
