#!/usr/bin/env python3
"""Register and select reusable character packages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import HEX_COLOR, InputError, require_text, write_json
from registry_common import (
    copy_asset,
    load_object,
    print_json,
    read_current,
    utc_now,
    validate_slug,
    write_current,
)


CURRENT = "current-character.json"
MANIFEST = "character.json"


def directory(root: Path, slug: str) -> Path:
    return root.expanduser().resolve() / "characters" / validate_slug(slug)


def resolve(root: Path, slug: str, *, allow_draft: bool = False) -> dict:
    folder = directory(root, slug)
    manifest = load_object(folder / MANIFEST)
    if manifest.get("status") != "confirmed" and not allow_draft:
        raise InputError(f"人物 {slug} 尚未确认")
    assets = manifest.get("assets")
    if not isinstance(assets, dict):
        raise InputError("人物档案缺少 assets")
    resolved: dict[str, str] = {}
    for key in ("sheet", "clean_reference", "spec"):
        value = require_text(assets.get(key), f"assets.{key}", limit=300)
        path = (folder / value).resolve()
        try:
            path.relative_to(folder.resolve())
        except ValueError as exc:
            raise InputError(f"人物资产路径越界: {key}") from exc
        if not path.is_file():
            raise InputError(f"人物资产不存在: {path}")
        resolved[key] = str(path)
    result = dict(manifest)
    result["assets"] = resolved
    result["manifest_path"] = str((folder / MANIFEST).resolve())
    return result


def register(args: argparse.Namespace) -> None:
    root = Path(args.root)
    folder = directory(root, args.slug)
    folder.mkdir(parents=True, exist_ok=True)
    old = load_object(folder / MANIFEST) if (folder / MANIFEST).exists() else {}
    theme_color = args.theme_color.upper() if args.theme_color else ""
    if theme_color and not HEX_COLOR.fullmatch(theme_color):
        raise InputError("theme-color 必须是 #RRGGBB")
    now = utc_now()
    manifest = {
        "version": 1,
        "slug": validate_slug(args.slug),
        "name": require_text(args.name, "name", limit=40),
        "author_name": require_text(args.name, "name", limit=40),
        "theme_color": theme_color,
        "theme_color_source": "user" if theme_color else "pending",
        "status": "draft",
        "revision": int(old.get("revision", 0)) + 1,
        "created_at": old.get("created_at", now),
        "updated_at": now,
        "confirmed_at": None,
        "assets": {
            "sheet": copy_asset(args.sheet, folder, "character-sheet"),
            "clean_reference": copy_asset(args.clean_reference, folder, "character-reference-clean"),
            "spec": copy_asset(args.spec, folder, "character-spec", ".md"),
        },
    }
    write_json(folder / MANIFEST, manifest)
    print_json(resolve(root, args.slug, allow_draft=True))


def confirm(args: argparse.Namespace) -> None:
    root = Path(args.root)
    resolve(root, args.slug, allow_draft=True)
    path = directory(root, args.slug) / MANIFEST
    manifest = load_object(path)
    now = utc_now()
    manifest.update(status="confirmed", updated_at=now, confirmed_at=now)
    write_json(path, manifest)
    write_current(root, CURRENT, args.slug, path)
    print_json(resolve(root, args.slug))


def activate(args: argparse.Namespace) -> None:
    root = Path(args.root)
    value = resolve(root, args.slug)
    write_current(root, CURRENT, args.slug, directory(root, args.slug) / MANIFEST)
    print_json(value)


def resolve_command(args: argparse.Namespace) -> None:
    root = Path(args.root)
    slug = args.slug or read_current(root, CURRENT)
    print_json(resolve(root, slug, allow_draft=args.allow_draft))


def list_command(args: argparse.Namespace) -> None:
    root = Path(args.root).expanduser().resolve()
    try:
        active = read_current(root, CURRENT)
    except InputError:
        active = None
    items = []
    for path in sorted((root / "characters").glob(f"*/{MANIFEST}")):
        try:
            value = load_object(path)
        except InputError:
            continue
        items.append(
            {
                "slug": value.get("slug"),
                "name": value.get("name"),
                "status": value.get("status"),
                "revision": value.get("revision"),
                "active": value.get("slug") == active,
            }
        )
    print_json(items)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    item = commands.add_parser("register")
    for name in ("root", "slug", "name", "sheet", "clean-reference", "spec"):
        item.add_argument(f"--{name}", required=True)
    item.add_argument("--theme-color")
    item.set_defaults(handler=register)
    for name, handler in (("confirm", confirm), ("activate", activate)):
        item = commands.add_parser(name)
        item.add_argument("--root", required=True)
        item.add_argument("--slug", required=True)
        item.set_defaults(handler=handler)
    item = commands.add_parser("resolve")
    item.add_argument("--root", required=True)
    item.add_argument("--slug")
    item.add_argument("--allow-draft", action="store_true")
    item.set_defaults(handler=resolve_command)
    item = commands.add_parser("list")
    item.add_argument("--root", required=True)
    item.set_defaults(handler=list_command)
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
