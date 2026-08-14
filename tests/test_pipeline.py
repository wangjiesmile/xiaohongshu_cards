from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import collect_images  # noqa: E402
from common import InputError  # noqa: E402


class PipelineTests(unittest.TestCase):
    def run_script(self, name: str, *arguments: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / name), *(str(item) for item in arguments)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_pipeline_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            source_image = temp / "source.png"
            illustration = temp / "cover-illustration.png"
            body_image = temp / "detail.png"
            for path, size, color in (
                (source_image, (500, 500), "#2F6B5F"),
                (illustration, (1600, 900), "#D7EAE4"),
                (body_image, (1200, 600), "#EFEFEA"),
            ):
                image = Image.new("RGB", size, color)
                ImageDraw.Draw(image).rectangle((40, 40, size[0] - 40, size[1] - 40), outline="#202322", width=8)
                image.save(path)

            profiles = temp / "profiles"
            created = self.run_script(
                "profile.py",
                "create",
                "--root",
                profiles,
                "--slug",
                "demo-author",
                "--name",
                "演示作者",
                "--accent",
                "#2F6B5F",
                "--action",
                "讲解方法",
                "--character",
                source_image,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            confirmed = self.run_script(
                "profile.py", "confirm", "--root", profiles, "--slug", "demo-author"
            )
            self.assertEqual(confirmed.returncode, 0, confirmed.stderr)

            project = {
                "version": 1,
                "cover": {"title": "把复杂内容拆成清楚卡片", "illustration": illustration.name},
                "pages": [
                    {
                        "kicker": "核心方法",
                        "title": "先确定每一页的唯一结论",
                        "blocks": [
                            {"type": "paragraph", "text": "先完整阅读文章，再决定卡片页数。"},
                            {"type": "highlight", "text": "内容太多时增加页数，不牺牲可读性。"},
                            {"type": "bullet", "text": "保留条件、限制与必要证据"},
                            {"type": "image", "path": body_image.name, "caption": "页面结构示意"},
                        ],
                    }
                ],
            }
            project_path = temp / "project.json"
            project_path.write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
            output = temp / "output"
            rendered = self.run_script(
                "render.py", project_path, profiles / "demo-author" / "profile.json", output
            )
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            for filename in ("cover.png", "page-01.png"):
                with Image.open(output / filename) as image:
                    self.assertEqual(image.size, (1080, 1440))

            publish_copy = temp / "publish-copy.md"
            publish_copy.write_text(
                """## 推荐标题
复杂内容怎么拆成小红书卡片

## 备选标题
- 长文转卡片的清晰方法
- 卡片分页先做这一步
- 一页只讲一个结论

## 正文
从完整阅读开始，再安排每一页的结论与证据。

## 话题
#小红书图文 #内容创作 #知识卡片 #排版设计 #写作方法 #效率工具
""",
                encoding="utf-8",
            )
            checked = self.run_script("validate.py", project_path, output, publish_copy)
            self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_private_address_is_rejected(self) -> None:
        private_record = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
        with mock.patch.object(socket, "getaddrinfo", return_value=private_record):
            with self.assertRaises(InputError):
                collect_images.public_addresses("example.invalid", 80)

    def test_remote_credentials_and_custom_port_are_rejected(self) -> None:
        with self.assertRaises(InputError):
            collect_images.open_remote("https://user:pass@example.com/image.png")
        with self.assertRaises(InputError):
            collect_images.open_remote("https://example.com:8443/image.png")


if __name__ == "__main__":
    unittest.main()
