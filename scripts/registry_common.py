#!/usr/bin/env python3
"""Shared primitives for versioned character and card-style registries."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import InputError, SLUG, read_json, write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_slug(slug: str) -> str:
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise InputError("slug 只允许小写字母、数字和单个连字符")
    return slug


def next_asset_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    revision = 2
    while candidate.exists():
        candidate = directory / f"{stem}-v{revision}{suffix}"
        revision += 1
    return candidate


def copy_asset(source: str, directory: Path, stem: str, suffix: str | None = None) -> str:
    path = Path(source).expanduser().resolve()
    if not path.is_file():
        raise InputError(f"资产不存在: {path}")
    actual_suffix = suffix or path.suffix.lower()
    if not actual_suffix or len(actual_suffix) > 10:
        raise InputError(f"资产扩展名无效: {path}")
    destination = next_asset_path(directory, stem, actual_suffix)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    return destination.name


def load_object(path: Path) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise InputError(f"JSON 必须是对象: {path}")
    return value


def write_current(root: Path, filename: str, slug: str, manifest: Path) -> None:
    root = root.expanduser().resolve()
    write_json(
        root / filename,
        {
            "version": 1,
            "slug": validate_slug(slug),
            "manifest": str(manifest.relative_to(root)),
            "updated_at": utc_now(),
        },
    )


def read_current(root: Path, filename: str) -> str:
    current = load_object(root.expanduser().resolve() / filename)
    return validate_slug(current.get("slug"))


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))
