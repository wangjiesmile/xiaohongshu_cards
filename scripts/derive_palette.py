#!/usr/bin/env python3
"""Derive a stable card palette from a character image or chosen accent."""

from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageStat

from common import HEX_COLOR, InputError, require_text, write_json


def rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % rgb


def mix(rgb: tuple[int, int, int], target: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(value + (goal - value) * amount) for value, goal in zip(rgb, target))


def image_accent(path: Path) -> tuple[int, int, int]:
    try:
        with Image.open(path) as image:
            sample = image.convert("RGB").resize((80, 80))
    except OSError as exc:
        raise InputError(f"无法读取人物图片: {path}") from exc
    candidates: list[tuple[float, tuple[int, int, int]]] = []
    for red, green, blue in sample.getdata():
        hue, saturation, lightness = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
        if saturation < 0.28 or lightness < 0.18 or lightness > 0.84:
            continue
        candidates.append((saturation * (1 - abs(lightness - 0.5)), (red, green, blue)))
    if candidates:
        candidates.sort(reverse=True)
        top = [rgb for _, rgb in candidates[: max(1, len(candidates) // 8)]]
        return tuple(round(sum(pixel[index] for pixel in top) / len(top)) for index in range(3))
    mean = ImageStat.Stat(sample).mean
    return tuple(round(channel) for channel in mean)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--profile-name", required=True)
    parser.add_argument("--handle", default="")
    parser.add_argument("--brand-label", default="NOTES")
    parser.add_argument("--accent")
    args = parser.parse_args()
    try:
        if args.accent:
            if not HEX_COLOR.fullmatch(args.accent):
                raise InputError("accent 必须是 #RRGGBB")
            accent = ImageColor.getrgb(args.accent)
            source = "user"
        else:
            accent = image_accent(Path(args.image).expanduser().resolve())
            source = "image"
        theme = {
            "version": 1,
            "profileName": require_text(args.profile_name, "profile-name", limit=40),
            "handle": args.handle.strip()[:80],
            "brandLabel": require_text(args.brand_label, "brand-label", limit=30),
            "accentSource": source,
            "palette": {
                "paper": "#FAFAF7",
                "panel": "#FFFFFF",
                "accent": rgb_hex(accent),
                "deepAccent": rgb_hex(mix(accent, (0, 0, 0), 0.48)),
                "softAccent": rgb_hex(mix(accent, (255, 255, 255), 0.86)),
                "ink": "#171A19",
                "body": "#2B302E",
                "muted": "#6B716E",
                "line": "#D7DBD7",
            },
        }
        write_json(Path(args.out).expanduser().resolve(), theme)
        print(Path(args.out).expanduser().resolve())
        return 0
    except (InputError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
