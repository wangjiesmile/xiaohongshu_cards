#!/usr/bin/env python3
"""Render validated card projects as 1080 by 1440 PNG files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

from common import HEX_COLOR, InputError, read_json, require_text, resolve_inside, validate_profile, validate_project


WIDTH, HEIGHT = 1080, 1440
MARGIN = 84
FONT_CANDIDATES = (
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
)


def font_path() -> Path:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return path
    raise InputError("未找到中文字体，请安装 PingFang、微软雅黑或 Noto Sans CJK")


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = font_path()
    index = 1 if bold and path.suffix.lower() in {".ttc", ".otc"} else 0
    try:
        return ImageFont.truetype(str(path), size=size, index=index)
    except OSError:
        return ImageFont.truetype(str(path), size=size)


def derived_colors(accent: str) -> tuple[str, str, str]:
    red, green, blue = ImageColor.getrgb(accent)
    dark = tuple(max(0, int(channel * 0.52)) for channel in (red, green, blue))
    pale = tuple(int(channel + (255 - channel) * 0.87) for channel in (red, green, blue))
    return accent, "#%02X%02X%02X" % dark, "#%02X%02X%02X" % pale


def split_text(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for character in paragraph:
            candidate = current + character
            if current and draw.textlength(candidate, font=face) > width:
                lines.append(current.rstrip())
                current = character.lstrip()
            else:
                current = candidate
        if current:
            lines.append(current.rstrip())
    return lines


def draw_lines(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    face: ImageFont.FreeTypeFont,
    fill: str,
    width: int,
    spacing: int,
    *,
    max_lines: int | None = None,
) -> int:
    lines = split_text(draw, text, face, width)
    if max_lines is not None and len(lines) > max_lines:
        raise InputError(f"文本超出允许行数（{len(lines)} > {max_lines}），请拆分页面")
    x, y = position
    line_height = face.size + spacing
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += line_height
    return y


def load_rgb(path: Path) -> Image.Image:
    try:
        with Image.open(path) as source:
            return ImageOps.exif_transpose(source).convert("RGB")
    except OSError as exc:
        raise InputError(f"无法读取图片: {path}") from exc


def rounded_image(image: Image.Image, size: tuple[int, int], radius: int = 24) -> Image.Image:
    fitted = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *size), radius=radius, fill=255)
    fitted.putalpha(mask)
    return fitted


def load_profile(profile_path: Path, *, allow_draft: bool = False) -> dict:
    base = profile_path.parent
    raw = read_json(profile_path)
    if not isinstance(raw, dict):
        raise InputError("profile 必须是 JSON 对象")
    if "accent" in raw:
        profile = validate_profile(raw, base=base)
        profile["author_name"] = profile["name"]
        profile["card_action"] = profile["action"]
        profile["_character_path"] = str(resolve_inside(base, profile["character"], "profile.character"))
        return profile
    status = raw.get("status")
    if status not in {"draft", "confirmed"}:
        raise InputError("profile.status 必须是 draft 或 confirmed")
    if status != "confirmed" and not allow_draft:
        raise InputError("卡片样式尚未确认；样稿请使用 --allow-draft")
    assets = raw.get("assets")
    if not isinstance(assets, dict):
        raise InputError("profile.assets 必须是对象")
    resolved_assets: dict[str, Path] = {}
    for key in ("card_pose", "theme"):
        value = require_text(assets.get(key), f"profile.assets.{key}", limit=300)
        candidate = Path(value)
        path = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
        if not candidate.is_absolute():
            try:
                path.relative_to(base.resolve())
            except ValueError as exc:
                raise InputError(f"profile.assets.{key} 路径越界") from exc
        if not path.is_file():
            raise InputError(f"样式资产不存在: {path}")
        resolved_assets[key] = path
    theme = read_json(resolved_assets["theme"])
    palette = theme.get("palette") if isinstance(theme, dict) else None
    accent = palette.get("accent") if isinstance(palette, dict) else None
    if not isinstance(accent, str) or not HEX_COLOR.fullmatch(accent):
        raise InputError("theme.palette.accent 必须是 #RRGGBB")
    return {
        "status": status,
        "name": require_text(raw.get("name"), "profile.name", limit=40),
        "author_name": require_text(raw.get("author_name"), "profile.author_name", limit=40),
        "card_action": require_text(raw.get("card_action"), "profile.card_action", limit=120),
        "accent": accent.upper(),
        "account": str(theme.get("handle", "")).strip()[:80],
        "_character_path": str(resolved_assets["card_pose"]),
    }


def render_cover(project: dict, profile: dict, base: Path) -> Image.Image:
    accent, dark, pale = derived_colors(profile["accent"])
    canvas = Image.new("RGB", (WIDTH, HEIGHT), accent)
    draw = ImageDraw.Draw(canvas)
    title_face = font(72, bold=True)
    title_lines = split_text(draw, project["cover"]["title"], title_face, WIDTH - MARGIN * 2)
    if len(title_lines) > 3:
        raise InputError("封面标题超过三行，请缩短标题")
    title_height = len(title_lines) * 90
    title_y = 104
    for line in title_lines:
        line_width = draw.textlength(line, font=title_face)
        draw.text(((WIDTH - line_width) / 2, title_y), line, font=title_face, fill="#FFFFFF")
        title_y += 90
    illustration_path = resolve_inside(base, project["cover"]["illustration"], "cover.illustration")
    window_x, window_y, window_w, window_h = 60, max(390, 130 + title_height), 960, 602
    if window_y + window_h > 1110:
        raise InputError("封面标题过长，无法容纳 16:9 窗口")
    draw.rounded_rectangle((window_x + 12, window_y + 18, window_x + window_w + 12, window_y + window_h + 18), radius=30, fill=dark)
    draw.rounded_rectangle((window_x, window_y, window_x + window_w, window_y + window_h), radius=28, fill="#F5F5F2")
    draw.rounded_rectangle((window_x, window_y, window_x + window_w, window_y + 62), radius=28, fill="#ECEDE9")
    draw.rectangle((window_x, window_y + 34, window_x + window_w, window_y + 62), fill="#ECEDE9")
    for offset, color in ((0, "#FF5F57"), (34, "#FEBB2E"), (68, "#28C840")):
        draw.ellipse((window_x + 26 + offset, window_y + 21, window_x + 44 + offset, window_y + 39), fill=color)
    illustration = rounded_image(load_rgb(illustration_path), (window_w, 540), 0)
    canvas.paste(illustration, (window_x, window_y + 62), illustration)
    author = profile["author_name"]
    author_face = font(46, bold=True)
    author_width = draw.textlength(author, font=author_face)
    draw.text(((WIDTH - author_width) / 2, 1225), author, font=author_face, fill="#FFFFFF")
    return canvas


def render_page(project: dict, page: dict, page_number: int, base: Path, accent: str) -> Image.Image:
    _, dark, pale = derived_colors(accent)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "#FAFAF7")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, WIDTH, 16), fill=accent)
    draw.text((MARGIN, 66), page["kicker"].upper(), font=font(23, bold=True), fill=accent)
    draw.text((WIDTH - MARGIN - 64, 58), f"{page_number:02d}", font=font(34, bold=True), fill=dark)
    y = draw_lines(draw, (MARGIN, 122), page["title"], font(55, bold=True), "#171A19", WIDTH - MARGIN * 2, 14, max_lines=3)
    y += 42
    for block in page["blocks"]:
        kind = block["type"]
        if kind == "spacer":
            y += block["height"]
            continue
        if kind == "image":
            image_path = resolve_inside(base, block["path"], "block.path")
            source = load_rgb(image_path)
            target_height = min(block.get("height", 360), int((WIDTH - MARGIN * 2) * source.height / source.width))
            if y + target_height + 72 > HEIGHT - 98:
                raise InputError(f"第 {page_number:02d} 页图片溢出，请拆分页面")
            fitted = ImageOps.contain(source, (WIDTH - MARGIN * 2, target_height), Image.Resampling.LANCZOS)
            x = (WIDTH - fitted.width) // 2
            canvas.paste(fitted, (x, y))
            y += fitted.height + 16
            if block.get("caption"):
                y = draw_lines(draw, (MARGIN, y), block["caption"], font(20), "#6B706E", WIDTH - MARGIN * 2, 8, max_lines=2)
            y += 26
            continue
        if kind == "highlight":
            lines = split_text(draw, block["text"], font(31, bold=True), WIDTH - MARGIN * 2 - 64)
            height = len(lines) * 44 + 52
            if y + height > HEIGHT - 98:
                raise InputError(f"第 {page_number:02d} 页重点块溢出，请拆分页面")
            draw.rounded_rectangle((MARGIN, y, WIDTH - MARGIN, y + height), radius=18, fill=pale)
            draw.rectangle((MARGIN, y, MARGIN + 10, y + height), fill=accent)
            draw_lines(draw, (MARGIN + 34, y + 24), block["text"], font(31, bold=True), dark, WIDTH - MARGIN * 2 - 64, 13)
            y += height + 28
            continue
        if kind == "item":
            label = " ".join(value for value in (block.get("number", ""), block["title"]) if value)
            text = f"{label}\n{block['body']}"
            face = font(27, bold=True)
        else:
            text = block["text"]
            face = font(25 if kind == "code" else (26 if kind == "section" else 29), bold=kind in {"bullet", "section", "note"})
        prefix = "•  " if kind == "bullet" else ""
        fill = dark if kind == "code" else "#282D2B"
        text = prefix + text
        lines = split_text(draw, text, face, WIDTH - MARGIN * 2 - (32 if kind == "code" else 0))
        panel_kind = kind in {"code", "note", "item"}
        height = len(lines) * (face.size + 14) + (36 if panel_kind else 0)
        if y + height > HEIGHT - 98:
            raise InputError(f"第 {page_number:02d} 页文字溢出，请拆分页面")
        if panel_kind:
            panel_fill = pale if kind == "note" else "#EEF0ED"
            draw.rounded_rectangle((MARGIN, y, WIDTH - MARGIN, y + height), radius=14, fill=panel_fill)
            draw_lines(draw, (MARGIN + 20, y + 18), text, face, fill, WIDTH - MARGIN * 2 - 40, 14)
        else:
            draw_lines(draw, (MARGIN, y), text, face, fill, WIDTH - MARGIN * 2, 14)
        y += height + 22
    draw.line((MARGIN, HEIGHT - 72, WIDTH - MARGIN, HEIGHT - 72), fill="#D6D9D5", width=2)
    draw.text((MARGIN, HEIGHT - 58), project["cover"]["title"], font=font(17), fill="#777D79")
    return canvas


def save_all(
    project_path: Path,
    profile_path: Path,
    output: Path,
    *,
    allow_draft: bool = False,
    cover_only: bool = False,
) -> list[Path]:
    project_base = project_path.parent
    project = validate_project(read_json(project_path), base=project_base, allow_empty=cover_only)
    profile = load_profile(profile_path, allow_draft=allow_draft)
    if not cover_only and project["cover"]["status"] != "confirmed":
        raise InputError("封面尚未确认；请先生成封面样稿并把 cover.status 改为 confirmed")
    output.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    cover_path = output / "cover.png"
    render_cover(project, profile, project_base).save(cover_path, format="PNG", optimize=True)
    files.append(cover_path)
    if cover_only:
        return files
    for index, page in enumerate(project["pages"], start=1):
        path = output / f"card-{index:02d}.png"
        render_page(project, page, index, project_base, profile["accent"]).save(path, format="PNG", optimize=True)
        files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("profile", nargs="?")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--cover-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            path = font_path()
            print(f"Pillow {Image.__version__}; 字体 {path}")
            return 0
        if not all((args.project, args.profile, args.output)):
            parser.error("渲染时必须提供 project、profile 和 output")
        files = save_all(
            Path(args.project).expanduser().resolve(),
            Path(args.profile).expanduser().resolve(),
            Path(args.output).expanduser().resolve(),
            allow_draft=args.allow_draft,
            cover_only=args.cover_only,
        )
        print("\n".join(str(path) for path in files))
        return 0
    except (InputError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
