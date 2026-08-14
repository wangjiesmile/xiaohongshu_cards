#!/usr/bin/env python3
"""Shared validation and file helpers for the card pipeline."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BLOCK_TYPES = {
    "paragraph",
    "highlight",
    "section",
    "item",
    "bullet",
    "code",
    "image",
    "note",
    "spacer",
}


class InputError(ValueError):
    """Raised when a user-controlled project file is invalid."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"文件不存在: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"JSON 格式错误: {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def require_text(value: Any, field: str, *, limit: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field} 必须是非空文本")
    text = value.strip()
    if len(text) > limit:
        raise InputError(f"{field} 不能超过 {limit} 个字符")
    return text


def bounded_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise InputError(f"{field} 必须是整数")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise InputError(f"{field} 必须是整数") from exc
    return max(minimum, min(maximum, number))


def resolve_inside(base: Path, raw_path: str, field: str) -> Path:
    """Resolve a relative path while preventing traversal outside base."""
    candidate = Path(require_text(raw_path, field, limit=500))
    if candidate.is_absolute():
        raise InputError(f"{field} 必须是相对路径")
    base_resolved = base.resolve()
    target = (base_resolved / candidate).resolve()
    try:
        target.relative_to(base_resolved)
    except ValueError as exc:
        raise InputError(f"{field} 不能指向项目目录之外") from exc
    return target


def validate_profile(data: Any, *, base: Path) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise InputError("人物档案必须是 JSON 对象")
    slug = require_text(data.get("slug"), "profile.slug", limit=80)
    if not SLUG.fullmatch(slug):
        raise InputError("profile.slug 只允许小写字母、数字和连字符")
    status = data.get("status")
    if status not in {"draft", "confirmed"}:
        raise InputError("profile.status 必须是 draft 或 confirmed")
    accent = require_text(data.get("accent"), "profile.accent", limit=7)
    if not HEX_COLOR.fullmatch(accent):
        raise InputError("profile.accent 必须是 #RRGGBB")
    character_raw = require_text(data.get("character"), "profile.character", limit=500)
    character = resolve_inside(base, character_raw, "profile.character")
    if not character.is_file():
        raise InputError(f"人物图不存在: {character}")
    return {
        "version": 1,
        "slug": slug,
        "name": require_text(data.get("name"), "profile.name", limit=40),
        "accent": accent.upper(),
        "action": require_text(data.get("action"), "profile.action", limit=120),
        "character": character_raw,
        "account": str(data.get("account", "")).strip()[:80],
        "status": status,
    }


def validate_project(data: Any, *, base: Path, allow_empty: bool = False) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise InputError("项目数据必须是 JSON 对象")
    modern = "cards" in data
    if data.get("version", 1) != 1:
        raise InputError("project.version 必须为 1")
    cover = data.get("cover")
    if not isinstance(cover, dict):
        raise InputError("project.cover 必须是对象")
    illustration_raw = require_text(
        cover.get("illustration"), "cover.illustration", limit=500
    )
    illustration = resolve_inside(base, illustration_raw, "cover.illustration")
    if not illustration.is_file():
        raise InputError(f"封面插图不存在: {illustration}")
    cover_status = cover.get("status", "draft" if modern else "confirmed")
    if cover_status not in {"draft", "confirmed"}:
        raise InputError("cover.status 必须是 draft 或 confirmed")

    pages = data.get("cards") if modern else data.get("pages")
    if not isinstance(pages, list) or (not pages and not allow_empty):
        raise InputError("project.cards 必须是非空数组")
    normalized_pages: list[dict[str, Any]] = []
    for page_index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise InputError(f"pages[{page_index}] 必须是对象")
        blocks = page.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            raise InputError(f"pages[{page_index}].blocks 必须是非空数组")
        normalized_blocks: list[dict[str, str]] = []
        image_count = 0
        for block_index, block in enumerate(blocks, start=1):
            field = f"pages[{page_index}].blocks[{block_index}]"
            block_type_value = block.get("kind") if modern else block.get("type")
            if not isinstance(block, dict) or block_type_value not in BLOCK_TYPES:
                raise InputError(f"{field}.type 不受支持")
            block_type = str(block_type_value)
            if block_type == "image":
                image_count += 1
                raw = require_text(block.get("path"), f"{field}.path", limit=500)
                image = resolve_inside(base, raw, f"{field}.path")
                if not image.is_file():
                    raise InputError(f"正文图片不存在: {image}")
                normalized_blocks.append(
                    {
                        "type": block_type,
                        "path": raw,
                        "caption": str(block.get("caption", "")).strip()[:160],
                        "height": bounded_int(block.get("height", 360), f"{field}.height", 220, 520),
                    }
                )
            elif block_type == "spacer":
                normalized_blocks.append(
                    {"type": block_type, "height": bounded_int(block.get("height", 20), f"{field}.height", 8, 80)}
                )
            elif block_type == "item":
                title = require_text(block.get("title"), f"{field}.title", limit=120)
                body = require_text(block.get("body"), f"{field}.body", limit=1000)
                number = str(block.get("number", "")).strip()[:12]
                normalized_blocks.append(
                    {"type": block_type, "number": number, "title": title, "body": body}
                )
            else:
                normalized_blocks.append(
                    {
                        "type": block_type,
                        "text": require_text(
                            block.get("text"), f"{field}.text", limit=3000
                        ),
                    }
                )
        if image_count > 1:
            raise InputError(f"pages[{page_index}] 最多包含一张图片")
        normalized_pages.append(
            {
                "kicker": require_text(
                    page.get("eyebrow") if modern else page.get("kicker"),
                    f"pages[{page_index}].kicker",
                    limit=50,
                ),
                "title": require_text(
                    page.get("title"), f"pages[{page_index}].title", limit=80
                ),
                "blocks": normalized_blocks,
            }
        )
    return {
        "version": 1,
        "cover": {
            "title": require_text(cover.get("title"), "cover.title", limit=40),
            "illustration": illustration_raw,
            "status": cover_status,
        },
        "series_title": str(data.get("seriesTitle", cover.get("title", ""))).strip()[:80],
        "handle": str(data.get("handle", "")).strip()[:80],
        "pages": normalized_pages,
    }
