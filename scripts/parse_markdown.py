#!/usr/bin/env python3
"""Parse article title, headings, and a contextual Markdown image inventory."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from common import InputError, write_json


FRONTMATTER_TITLE = re.compile(r"^title\s*:\s*[\"']?(.+?)[\"']?\s*$", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+[\"']([^\"']*)[\"'])?\s*\)")
HTML_IMAGE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
HTML_ALT = re.compile(r"\balt\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)
KEEP_SIGNALS = (
    "截图", "图表", "流程", "架构", "步骤", "结果", "验证", "对比", "示意", "界面",
    "终端", "点击", "输入", "选择", "运行", "配置", "安装", "完成", "diagram", "chart",
    "result", "screenshot", "before", "after",
)
SKIP_SIGNALS = ("头像", "logo", "封面", "装饰", "二维码", "表情", "avatar", "cover", "emoji", "watermark")


def plain_text(value: str) -> str:
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"^[>*_`#\-\s]+|[>*_`#\-\s]+$", "", value.strip())
    return re.sub(r"\s+", " ", value).strip()


def nearby(lines: list[str], index: int) -> tuple[str, str]:
    before = next((plain_text(lines[pos]) for pos in range(index - 1, max(-1, index - 4), -1) if plain_text(lines[pos])), "")
    after = next((plain_text(lines[pos]) for pos in range(index + 1, min(len(lines), index + 4)) if plain_text(lines[pos])), "")
    return before, after


def local_source(raw: str, markdown: Path) -> tuple[str | None, bool]:
    parsed = urlsplit(raw)
    if parsed.scheme in {"http", "https"}:
        return None, True
    if parsed.scheme:
        return None, False
    source = Path(unquote(raw))
    if not source.is_absolute():
        source = markdown.parent / source
    return str(source.resolve()), False


def parse(path: Path) -> dict[str, object]:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InputError(f"Markdown 不存在: {path}") from exc
    if not source.strip():
        raise InputError("Markdown 不能为空")
    lines = source.splitlines()
    title: str | None = None
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            match = FRONTMATTER_TITLE.match(line.strip())
            if match:
                title = match.group(1).strip()
                break
    headings: list[dict[str, object]] = []
    images: list[dict[str, object]] = []
    seen: set[str] = set()
    fenced = False
    for line_index, line in enumerate(lines):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = HEADING.match(line)
        if heading:
            headings.append({"level": len(heading.group(1)), "text": heading.group(2).strip(), "line": line_index + 1})
            if title is None and len(heading.group(1)) == 1:
                title = heading.group(2).strip()
        matches: list[tuple[str, str, str]] = []
        for match in MARKDOWN_IMAGE.finditer(line):
            matches.append((match.group(1).strip(), (match.group(2) or match.group(3)).strip(), (match.group(4) or "").strip()))
        for match in HTML_IMAGE.finditer(line):
            alt = HTML_ALT.search(match.group(0))
            matches.append(((alt.group(1).strip() if alt else ""), match.group(1).strip(), ""))
        before, after = nearby(lines, line_index)
        for alt, raw, image_title in matches:
            context = " ".join(value for value in (alt, image_title, before, after) if value).lower()
            if raw in seen:
                hint, reason = "skip", "重复图片"
            elif any(signal in context for signal in SKIP_SIGNALS):
                hint, reason = "skip", "上下文显示为装饰、头像、Logo 或封面"
            elif any(signal in context for signal in KEEP_SIGNALS):
                hint, reason = "keep", "上下文包含步骤、截图、图表、结果或验证信号"
            elif line_index < 10 and not alt:
                hint, reason = "review", "靠近文章开头且缺少说明，可能是装饰封面"
            else:
                hint, reason = "review", "需要结合全文和图片内容判断"
            seen.add(raw)
            resolved, remote = local_source(raw, path)
            images.append(
                {
                    "index": len(images) + 1,
                    "line": line_index + 1,
                    "alt": alt,
                    "title": image_title,
                    "source": raw,
                    "resolved_source": resolved,
                    "remote": remote,
                    "context_before": before,
                    "context_after": after,
                    "selection_hint": hint,
                    "selection_reason": reason,
                }
            )
    return {
        "version": 1,
        "source": str(path.resolve()),
        "title": title or path.stem,
        "headings": headings,
        "images": images,
        "cleaned_markdown": source.rstrip() + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown")
    parser.add_argument("--output")
    parser.add_argument("--write-clean")
    args = parser.parse_args()
    try:
        result = parse(Path(args.markdown).expanduser().resolve())
        if args.write_clean:
            clean = Path(args.write_clean).expanduser().resolve()
            clean.parent.mkdir(parents=True, exist_ok=True)
            clean.write_text(str(result["cleaned_markdown"]), encoding="utf-8")
        if args.output:
            write_json(Path(args.output).expanduser().resolve(), result)
        else:
            import json

            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (InputError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
