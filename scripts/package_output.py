#!/usr/bin/env python3
"""Validate and package a complete Xiaohongshu card delivery as ZIP."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from common import InputError
from validate import validate_all


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("output")
    parser.add_argument("publish_copy")
    parser.add_argument("zip_path")
    args = parser.parse_args()
    try:
        project = Path(args.project).expanduser().resolve()
        output = Path(args.output).expanduser().resolve()
        publish_copy = Path(args.publish_copy).expanduser().resolve()
        archive = Path(args.zip_path).expanduser().resolve()
        files = validate_all(project, output, publish_copy)
        root = project.parent
        archive.parent.mkdir(parents=True, exist_ok=True)
        candidates = [project, publish_copy, *files]
        assets = root / "assets" / "article-images"
        if assets.is_dir():
            candidates.extend(path for path in assets.rglob("*") if path.is_file())
        illustration = root / "cover-illustration.png"
        if illustration.is_file():
            candidates.append(illustration)
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(set(candidates)):
                try:
                    relative = path.relative_to(root)
                except ValueError as exc:
                    raise InputError(f"打包文件不在文章目录内: {path}") from exc
                bundle.write(path, relative.as_posix())
        print(archive)
        return 0
    except (InputError, OSError, zipfile.BadZipFile) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
