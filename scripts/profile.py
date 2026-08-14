#!/usr/bin/env python3
"""Create, confirm, and inspect reusable character profiles."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from common import HEX_COLOR, InputError, SLUG, read_json, validate_profile, write_json


def profile_dir(root: Path, slug: str) -> Path:
    if not SLUG.fullmatch(slug):
        raise InputError("slug 只允许小写字母、数字和连字符")
    return root.resolve() / slug


def create(args: argparse.Namespace) -> None:
    if not HEX_COLOR.fullmatch(args.accent):
        raise InputError("accent 必须是 #RRGGBB")
    source = Path(args.character).expanduser().resolve()
    if not source.is_file():
        raise InputError(f"人物图不存在: {source}")
    destination_dir = profile_dir(Path(args.root), args.slug)
    destination_dir.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise InputError("人物图只支持 PNG、JPEG 或 WebP")
    character_name = f"character{suffix}"
    shutil.copyfile(source, destination_dir / character_name)
    data = {
        "version": 1,
        "slug": args.slug,
        "name": args.name,
        "accent": args.accent.upper(),
        "action": args.action,
        "character": character_name,
        "account": args.account or "",
        "status": "draft",
    }
    validated = validate_profile(data, base=destination_dir)
    write_json(destination_dir / "profile.json", validated)
    print(destination_dir / "profile.json")


def confirm(args: argparse.Namespace) -> None:
    directory = profile_dir(Path(args.root), args.slug)
    path = directory / "profile.json"
    data = validate_profile(read_json(path), base=directory)
    data["status"] = "confirmed"
    write_json(path, data)
    print(path)


def show(args: argparse.Namespace) -> None:
    directory = profile_dir(Path(args.root), args.slug)
    path = directory / "profile.json"
    data = validate_profile(read_json(path), base=directory)
    import json

    print(json.dumps(data, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    sub = command.add_subparsers(dest="command", required=True)

    create_parser = sub.add_parser("create", help="创建 draft 人物档案")
    create_parser.add_argument("--root", required=True)
    create_parser.add_argument("--slug", required=True)
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--accent", required=True)
    create_parser.add_argument("--action", required=True)
    create_parser.add_argument("--character", required=True)
    create_parser.add_argument("--account")
    create_parser.set_defaults(handler=create)

    for name, handler in (("confirm", confirm), ("show", show)):
        item = sub.add_parser(name)
        item.add_argument("--root", required=True)
        item.add_argument("--slug", required=True)
        item.set_defaults(handler=handler)
    return command


def main() -> int:
    try:
        args = parser().parse_args()
        args.handler(args)
        return 0
    except InputError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
