#!/usr/bin/env python3
"""Collect selected Markdown images with SSRF and path-traversal protection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit

from collect_images import copy_local, copy_remote
from common import InputError, write_json
from parse_markdown import parse


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown")
    parser.add_argument("output_dir")
    parser.add_argument("--indexes", required=True)
    parser.add_argument("--manifest")
    args = parser.parse_args()
    try:
        markdown = Path(args.markdown).expanduser().resolve()
        analysis = parse(markdown)
        images = {item["index"]: item for item in analysis["images"]}
        indexes = [int(value.strip()) for value in args.indexes.split(",") if value.strip()]
        if not indexes or len(indexes) != len(set(indexes)) or min(indexes) < 1:
            raise InputError("indexes 必须是互不重复的正整数")
        output = Path(args.output_dir).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        manifest = []
        for index in indexes:
            item = images.get(index)
            if not item:
                raise InputError(f"找不到图片序号: {index}")
            raw = str(item["source"])
            stem = output / f"image-{index:02d}"
            if urlsplit(raw).scheme:
                filename = copy_remote(raw, stem)
                action = "downloaded"
            else:
                filename = copy_local(raw, markdown.parent, stem)
                action = "copied"
            manifest.append(
                {
                    "index": index,
                    "source": raw,
                    "file": filename,
                    "output": str((output / filename).resolve()),
                    "alt": item.get("alt", ""),
                    "action": action,
                }
            )
        manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else output / "manifest.json"
        write_json(manifest_path, {"version": 1, "images": manifest})
        print(manifest_path)
        return 0
    except (InputError, OSError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
