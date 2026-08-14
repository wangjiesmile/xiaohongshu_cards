#!/usr/bin/env python3
"""Render a 1080 by 1440 card-style sample before article production."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageOps

from common import HEX_COLOR, InputError, read_json, require_text
from render import HEIGHT, MARGIN, WIDTH, derived_colors, draw_lines, font, load_rgb


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", required=True)
    parser.add_argument("--card-pose", required=True)
    parser.add_argument("--author-name", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        theme = read_json(Path(args.theme).expanduser().resolve())
        palette = theme.get("palette") if isinstance(theme, dict) else None
        accent = palette.get("accent") if isinstance(palette, dict) else None
        if not isinstance(accent, str) or not HEX_COLOR.fullmatch(accent):
            raise InputError("theme.palette.accent 必须是 #RRGGBB")
        author = require_text(args.author_name, "author-name", limit=40)
        action = require_text(args.action, "action", limit=120)
        pose_path = Path(args.card_pose).expanduser().resolve()
        pose = load_rgb(pose_path)
        _, dark, pale = derived_colors(accent)
        canvas = Image.new("RGB", (WIDTH, HEIGHT), "#FAFAF7")
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 0, WIDTH, 18), fill=accent)
        draw.text((MARGIN, 68), "STYLE PREVIEW", font=font(23, bold=True), fill=accent)
        draw.text((WIDTH - MARGIN - 64, 60), "01", font=font(34, bold=True), fill=dark)
        y = draw_lines(draw, (MARGIN, 130), "一页只表达一个主要结论", font(55, bold=True), "#171A19", 620, 14, max_lines=3)
        y += 44
        draw.rounded_rectangle((MARGIN, y, 670, y + 170), radius=18, fill=pale)
        draw.rectangle((MARGIN, y, MARGIN + 10, y + 170), fill=accent)
        draw_lines(draw, (MARGIN + 34, y + 28), "主题色驱动标题、重点框、编号和分区线。", font(30, bold=True), dark, 520, 13, max_lines=3)
        y += 214
        y = draw_lines(draw, (MARGIN, y), "正文保持稳定字号和留白。内容过多时增加页数，不把文字缩小到难以阅读。", font(29), "#2B302E", 590, 14, max_lines=4)
        draw.text((MARGIN, y + 30), f"动作：{action}", font=font(22), fill="#69706D")
        fitted = ImageOps.contain(pose, (350, 620), Image.Resampling.LANCZOS)
        mask = Image.new("L", fitted.size, 255)
        canvas.paste(fitted, (WIDTH - MARGIN - fitted.width, 650), mask)
        draw.line((MARGIN, HEIGHT - 88, WIDTH - MARGIN, HEIGHT - 88), fill="#D6D9D5", width=2)
        draw.text((MARGIN, HEIGHT - 70), author, font=font(20, bold=True), fill=dark)
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output, format="PNG", optimize=True)
        print(output)
        return 0
    except (InputError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
