#!/usr/bin/env python3
"""Validate a project, rendered PNG set, and Xiaohongshu publish copy."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from PIL import Image

from common import InputError, read_json, validate_project


SECTIONS = ("推荐标题", "备选标题", "正文", "话题")


def validate_copy(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InputError(f"发布文案不存在: {path}") from exc
    if re.search(r"^#[ \t]+推荐标题[ \t]*$", text, re.MULTILINE) and re.search(
        r"^#[ \t]+正文[ \t]*$", text, re.MULTILINE
    ) and re.search(r"^#[ \t]+Tags[ \t]*$", text, re.MULTILINE | re.IGNORECASE):
        topic_count = len(re.findall(r"(?<!\w)#[^#\s]+", text.split("Tags", 1)[-1]))
        if not 6 <= topic_count <= 10:
            raise InputError("Tags 必须为六至十个")
        return
    positions: list[int] = []
    for section in SECTIONS:
        match = re.search(rf"^##[ \t]+{re.escape(section)}[ \t]*$", text, re.MULTILINE)
        if not match:
            raise InputError(f"发布文案缺少章节: ## {section}")
        positions.append(match.start())
    if positions != sorted(positions):
        raise InputError("发布文案章节顺序不正确")
    alternate = re.search(
        r"^##[ \t]+备选标题[ \t]*$([\s\S]*?)^##[ \t]+正文[ \t]*$",
        text,
        re.MULTILINE,
    )
    if not alternate:
        raise InputError("无法读取备选标题")
    title_lines = [line for line in alternate.group(1).splitlines() if line.strip().startswith(("-", "*"))]
    if len(title_lines) != 3:
        raise InputError("备选标题必须正好三条")
    topics = re.search(r"^##[ \t]+话题[ \t]*$([\s\S]*)$", text, re.MULTILINE)
    topic_count = len(re.findall(r"(?<!\w)#[^#\s]+", topics.group(1) if topics else ""))
    if not 6 <= topic_count <= 10:
        raise InputError("话题必须为六至十个")


def validate_png(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.load()
            if image.format != "PNG":
                raise InputError(f"文件不是 PNG: {path}")
            if image.size != (1080, 1440):
                raise InputError(f"图片尺寸不是 1080x1440: {path}")
    except OSError as exc:
        raise InputError(f"无法读取渲染图片: {path}") from exc


def validate_all(project_path: Path, output: Path, copy_path: Path) -> list[Path]:
    project = validate_project(read_json(project_path), base=project_path.parent)
    if project["cover"]["status"] != "confirmed":
        raise InputError("封面尚未确认")
    expected = [output / "cover.png"] + [
        output / f"card-{index:02d}.png" for index in range(1, len(project["pages"]) + 1)
    ]
    actual = sorted(output.glob("*.png")) if output.is_dir() else []
    if set(actual) != set(expected):
        missing = sorted(path.name for path in set(expected) - set(actual))
        extra = sorted(path.name for path in set(actual) - set(expected))
        raise InputError(f"渲染文件不匹配；缺少 {missing or '无'}；多出 {extra or '无'}")
    for path in expected:
        validate_png(path)
    referenced = {
        resolve_image(project_path.parent, block["path"])
        for page in project["pages"]
        for block in page["blocks"]
        if block["type"] == "image"
    }
    manifest_path = project_path.parent / "assets" / "article-images" / "manifest.json"
    if manifest_path.is_file():
        manifest = read_json(manifest_path)
        items = manifest.get("images") if isinstance(manifest, dict) else manifest
        if not isinstance(items, list):
            raise InputError("关键图 manifest 必须是数组或包含 images 数组")
        for item in items:
            if not isinstance(item, dict):
                raise InputError("关键图 manifest 项必须是对象")
            raw = item.get("output") or item.get("file")
            if not isinstance(raw, str) or not raw.strip():
                raise InputError("关键图 manifest 缺少 output")
            candidate = Path(raw)
            selected = candidate.resolve() if candidate.is_absolute() else (manifest_path.parent / candidate).resolve()
            if selected not in referenced:
                raise InputError(f"选中的关键图没有进入卡片: {selected}")
    validate_copy(copy_path)
    return expected


def resolve_image(base: Path, raw: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate.resolve()
    target = (base.resolve() / candidate).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError as exc:
        raise InputError("正文图片路径越界") from exc
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("output")
    parser.add_argument("publish_copy")
    args = parser.parse_args()
    try:
        files = validate_all(
            Path(args.project).expanduser().resolve(),
            Path(args.output).expanduser().resolve(),
            Path(args.publish_copy).expanduser().resolve(),
        )
        print(f"校验通过：{len(files)} 张图片")
        return 0
    except (InputError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
