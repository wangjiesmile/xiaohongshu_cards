#!/usr/bin/env python3
"""Render validated card projects as 1080 by 1440 PNG files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

from common import InputError, read_json, resolve_inside, validate_profile, validate_project


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


def render_cover(project: dict, profile: dict, base: Path) -> Image.Image:
    accent, dark, pale = derived_colors(profile["accent"])
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "#FAFAF7")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 26, HEIGHT), fill=accent)
    draw.text((MARGIN, 78), "XIAOHONGSHU NOTES", font=font(24, bold=True), fill=dark)
    draw.rounded_rectangle((MARGIN, 136, MARGIN + 126, 146), radius=5, fill=accent)
    y = draw_lines(
        draw,
        (MARGIN, 192),
        project["cover"]["title"],
        font(78, bold=True),
        "#161918",
        WIDTH - MARGIN * 2,
        18,
        max_lines=3,
    )
    illustration_path = resolve_inside(base, project["cover"]["illustration"], "cover.illustration")
    illustration = rounded_image(load_rgb(illustration_path), (WIDTH - MARGIN * 2, 513), 28)
    illustration_y = max(520, y + 46)
    if illustration_y + 513 > 1165:
        raise InputError("封面标题过长，无法容纳 16:9 插图")
    canvas.paste(illustration, (MARGIN, illustration_y), illustration)
    draw.rounded_rectangle((MARGIN, 1222, WIDTH - MARGIN, 1334), radius=22, fill=pale)
    character_path = resolve_inside(base=Path(profile["_base"]), raw_path=profile["character"], field="profile.character")
    character = rounded_image(load_rgb(character_path), (82, 82), 41)
    canvas.paste(character, (MARGIN + 18, 1237), character)
    draw.text((MARGIN + 120, 1242), profile["name"], font=font(34, bold=True), fill=dark)
    account = profile.get("account") or profile["action"]
    draw.text((MARGIN + 120, 1286), account, font=font(21), fill="#4E5552")
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
        if kind == "image":
            image_path = resolve_inside(base, block["path"], "block.path")
            source = load_rgb(image_path)
            target_height = min(430, int((WIDTH - MARGIN * 2) * source.height / source.width))
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
        face = font(25 if kind == "code" else 29, bold=kind == "bullet")
        prefix = "•  " if kind == "bullet" else ""
        fill = dark if kind == "code" else "#282D2B"
        text = prefix + block["text"]
        lines = split_text(draw, text, face, WIDTH - MARGIN * 2 - (32 if kind == "code" else 0))
        height = len(lines) * (face.size + 14) + (36 if kind == "code" else 0)
        if y + height > HEIGHT - 98:
            raise InputError(f"第 {page_number:02d} 页文字溢出，请拆分页面")
        if kind == "code":
            draw.rounded_rectangle((MARGIN, y, WIDTH - MARGIN, y + height), radius=14, fill="#EEF0ED")
            draw_lines(draw, (MARGIN + 20, y + 18), text, face, fill, WIDTH - MARGIN * 2 - 40, 14)
        else:
            draw_lines(draw, (MARGIN, y), text, face, fill, WIDTH - MARGIN * 2, 14)
        y += height + 22
    draw.line((MARGIN, HEIGHT - 72, WIDTH - MARGIN, HEIGHT - 72), fill="#D6D9D5", width=2)
    draw.text((MARGIN, HEIGHT - 58), project["cover"]["title"], font=font(17), fill="#777D79")
    return canvas


def save_all(project_path: Path, profile_path: Path, output: Path) -> list[Path]:
    project_base = project_path.parent
    profile_base = profile_path.parent
    project = validate_project(read_json(project_path), base=project_base)
    profile = validate_profile(read_json(profile_path), base=profile_base)
    if profile["status"] != "confirmed":
        raise InputError("人物档案尚未确认")
    profile["_base"] = str(profile_base)
    output.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    cover_path = output / "cover.png"
    render_cover(project, profile, project_base).save(cover_path, format="PNG", optimize=True)
    files.append(cover_path)
    for index, page in enumerate(project["pages"], start=1):
        path = output / f"page-{index:02d}.png"
        render_page(project, page, index, project_base, profile["accent"]).save(path, format="PNG", optimize=True)
        files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?")
    parser.add_argument("profile", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--check", action="store_true")
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
        )
        print("\n".join(str(path) for path in files))
        return 0
    except (InputError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
