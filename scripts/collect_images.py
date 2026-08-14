#!/usr/bin/env python3
"""Collect selected local or remote Markdown images into an asset directory."""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import mimetypes
import shutil
import socket
import ssl
import sys
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, UnidentifiedImageError

from common import InputError, read_json, resolve_inside, write_json


MAX_BYTES = 12 * 1024 * 1024
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def public_addresses(host: str, port: int) -> list[str]:
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise InputError(f"无法解析远程图片主机: {host}") from exc
    addresses: list[str] = []
    for record in records:
        address = record[4][0]
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise InputError(f"拒绝访问非公网地址: {host}")
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise InputError(f"远程图片主机没有可用公网地址: {host}")
    return addresses


def open_remote(url: str) -> tuple[http.client.HTTPResponse, http.client.HTTPConnection]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise InputError("远程图片只支持 HTTP 或 HTTPS")
    if parsed.username or parsed.password:
        raise InputError("远程图片 URL 不能包含凭据")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise InputError("远程图片端口无效") from exc
    if port not in {80, 443}:
        raise InputError("远程图片端口只允许 80 或 443")
    address = public_addresses(parsed.hostname, port)[0]
    host_header = parsed.hostname
    default_port = 443 if parsed.scheme == "https" else 80
    if port != default_port:
        host_header = f"{host_header}:{port}"
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"

    if parsed.scheme == "https":
        connection = http.client.HTTPSConnection(parsed.hostname, port, timeout=15)
        raw_socket = socket.create_connection((address, port), timeout=15)
        context = ssl.create_default_context()
        connection.sock = context.wrap_socket(raw_socket, server_hostname=parsed.hostname)
    else:
        connection = http.client.HTTPConnection(address, port, timeout=15)
    connection.request(
        "GET",
        path,
        headers={"Host": host_header, "User-Agent": "xiaohongshu-cards/1"},
    )
    response = connection.getresponse()
    if 300 <= response.status < 400:
        connection.close()
        raise InputError("远程图片不允许重定向")
    if response.status != 200:
        connection.close()
        raise InputError(f"远程图片返回 HTTP {response.status}")
    content_type = response.getheader("Content-Type", "").split(";", 1)[0].lower()
    if content_type not in ALLOWED_TYPES:
        connection.close()
        raise InputError(f"远程内容不是受支持的图片: {content_type or 'unknown'}")
    length = response.getheader("Content-Length")
    if length and int(length) > MAX_BYTES:
        connection.close()
        raise InputError("远程图片超过 12 MB")
    return response, connection


def copy_remote(url: str, destination: Path) -> str:
    response, connection = open_remote(url)
    content_type = response.getheader("Content-Type", "").split(";", 1)[0].lower()
    final_path = destination.with_suffix(ALLOWED_TYPES[content_type])
    total = 0
    try:
        with final_path.open("wb") as output:
            while chunk := response.read(64 * 1024):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise InputError("远程图片超过 12 MB")
                output.write(chunk)
        verify_image(final_path)
    except Exception:
        final_path.unlink(missing_ok=True)
        raise
    finally:
        connection.close()
    return final_path.name


def verify_image(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise InputError(f"文件不是有效图片: {path}") from exc


def copy_local(raw: str, source_root: Path, destination: Path) -> str:
    source = resolve_inside(source_root, raw, "image.source")
    if not source.is_file():
        raise InputError(f"本地图片不存在: {source}")
    suffix = source.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        guessed = mimetypes.guess_type(source.name)[0]
        suffix = ALLOWED_TYPES.get(guessed or "", "")
    if not suffix:
        raise InputError(f"不支持的本地图片格式: {source}")
    final_path = destination.with_suffix(suffix)
    shutil.copyfile(source, final_path)
    try:
        verify_image(final_path)
    except Exception:
        final_path.unlink(missing_ok=True)
        raise
    return final_path.name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis")
    parser.add_argument("assets_dir")
    parser.add_argument("--indexes", required=True, help="逗号分隔的图片序号")
    args = parser.parse_args()
    try:
        analysis_path = Path(args.analysis).expanduser().resolve()
        analysis = read_json(analysis_path)
        images = analysis.get("images") if isinstance(analysis, dict) else None
        if not isinstance(images, list):
            raise InputError("analysis.images 必须是数组")
        indexes = [int(part.strip()) for part in args.indexes.split(",") if part.strip()]
        if not indexes or len(indexes) != len(set(indexes)) or min(indexes) < 1:
            raise InputError("indexes 必须是互不重复的正整数")
        by_index = {item.get("index"): item for item in images if isinstance(item, dict)}
        output = Path(args.assets_dir).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        source_root = Path(str(analysis.get("source", analysis_path))).resolve().parent
        manifest: list[dict[str, object]] = []
        for index in indexes:
            item = by_index.get(index)
            if not item or not isinstance(item.get("source"), str):
                raise InputError(f"找不到图片序号: {index}")
            raw = str(item["source"])
            stem = output / f"image-{index:02d}"
            if urlsplit(raw).scheme:
                filename = copy_remote(raw, stem)
            else:
                filename = copy_local(raw, source_root, stem)
            manifest.append(
                {"index": index, "source": raw, "file": filename, "alt": item.get("alt", "")}
            )
        write_json(output / "manifest.json", {"version": 1, "images": manifest})
        print(output / "manifest.json")
        return 0
    except (InputError, OSError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
