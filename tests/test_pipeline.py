from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import unittest
import zipfile
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

    @staticmethod
    def image(path: Path, size: tuple[int, int], color: str) -> None:
        image = Image.new("RGB", size, color)
        ImageDraw.Draw(image).rectangle(
            (40, 40, size[0] - 40, size[1] - 40), outline="#202322", width=8
        )
        image.save(path)

    def test_three_gate_pipeline_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            article = temp / "article"
            article.mkdir()
            character_image = temp / "character.png"
            character_sheet = temp / "sheet.png"
            illustration = article / "cover-illustration.png"
            detail = article / "detail.png"
            for path, size, color in (
                (character_image, (500, 700), "#2F6B5F"),
                (character_sheet, (1200, 900), "#E4EFEB"),
                (illustration, (1600, 900), "#D7EAE4"),
                (detail, (1200, 600), "#EFEFEA"),
            ):
                self.image(path, size, color)
            spec = temp / "character-spec.md"
            spec.write_text("# 人物规范\n\n保持服装与配件一致。\n", encoding="utf-8")

            character_root = temp / ".xiaohongshu-character-assets"
            registered = self.run_script(
                "character_registry.py",
                "register",
                "--root",
                character_root,
                "--slug",
                "demo-author",
                "--name",
                "演示作者",
                "--theme-color",
                "#2F6B5F",
                "--sheet",
                character_sheet,
                "--clean-reference",
                character_image,
                "--spec",
                spec,
            )
            self.assertEqual(registered.returncode, 0, registered.stderr)
            unresolved = self.run_script(
                "character_registry.py", "resolve", "--root", character_root, "--slug", "demo-author"
            )
            self.assertNotEqual(unresolved.returncode, 0)
            confirmed = self.run_script(
                "character_registry.py", "confirm", "--root", character_root, "--slug", "demo-author"
            )
            self.assertEqual(confirmed.returncode, 0, confirmed.stderr)

            theme = temp / "theme.json"
            palette = self.run_script(
                "derive_palette.py",
                "--image",
                character_image,
                "--out",
                theme,
                "--profile-name",
                "演示作者",
                "--handle",
                "@demo",
                "--accent",
                "#2F6B5F",
            )
            self.assertEqual(palette.returncode, 0, palette.stderr)
            layout_sample = temp / "layout-sample.png"
            sample = self.run_script(
                "style_preview.py",
                "--theme",
                theme,
                "--card-pose",
                character_image,
                "--author-name",
                "演示作者",
                "--action",
                "站在白板前讲解",
                "--output",
                layout_sample,
            )
            self.assertEqual(sample.returncode, 0, sample.stderr)
            with Image.open(layout_sample) as image:
                self.assertEqual(image.size, (1080, 1440))
            profile_root = temp / ".xiaohongshu-card-profiles"
            profile = self.run_script(
                "profile_registry.py",
                "register",
                "--root",
                profile_root,
                "--slug",
                "demo-style",
                "--name",
                "演示样式",
                "--author-name",
                "演示作者",
                "--action",
                "站在白板前讲解",
                "--sheet",
                character_sheet,
                "--clean-reference",
                character_image,
                "--card-pose",
                character_image,
                "--spec",
                spec,
                "--theme",
                theme,
                "--layout-sample",
                layout_sample,
            )
            self.assertEqual(profile.returncode, 0, profile.stderr)
            profile_path = profile_root / "profiles" / "demo-style" / "profile.json"

            markdown = article / "source.md"
            markdown.write_text(
                """---
title: 把复杂内容拆成清楚卡片
---

# 备用标题

第一步先确认内容结构。

![操作步骤截图](detail.png)

完成后检查页面结果。
""",
                encoding="utf-8",
            )
            analysis = article / "analysis.json"
            parsed = self.run_script("parse_markdown.py", markdown, "--output", analysis)
            self.assertEqual(parsed.returncode, 0, parsed.stderr)
            parsed_data = json.loads(analysis.read_text(encoding="utf-8"))
            self.assertEqual(parsed_data["title"], "把复杂内容拆成清楚卡片")
            self.assertEqual(parsed_data["images"][0]["selection_hint"], "keep")
            assets = article / "assets" / "article-images"
            collected = self.run_script(
                "collect_markdown_images.py", markdown, assets, "--indexes", "1"
            )
            self.assertEqual(collected.returncode, 0, collected.stderr)

            project_path = article / "cards.json"
            created = self.run_script(
                "project.py",
                "create",
                "--output",
                project_path,
                "--series-title",
                "卡片方法",
                "--title",
                "把复杂内容拆成清楚卡片",
                "--illustration",
                illustration.name,
                "--handle",
                "@demo",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            project = json.loads(project_path.read_text(encoding="utf-8"))
            project["cards"] = [
                {
                    "kind": "content",
                    "eyebrow": "01 · 核心方法",
                    "title": "先确定每一页的唯一结论",
                    "blocks": [
                        {"kind": "paragraph", "text": "先完整阅读文章，再决定卡片页数。"},
                        {"kind": "highlight", "text": "内容太多时增加页数，不牺牲可读性。"},
                        {"kind": "section", "text": "执行顺序"},
                        {"kind": "item", "number": "01", "title": "梳理结构", "body": "保留条件与限制。"},
                        {"kind": "image", "path": "assets/article-images/image-01.png", "caption": "操作步骤截图", "height": 300},
                        {"kind": "note", "text": "完成后检查输出。"},
                    ],
                }
            ]
            project_path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

            output = article / "output"
            draft_profile_render = self.run_script(
                "render_cards.py", project_path, output, profile_path, "--cover-only"
            )
            self.assertNotEqual(draft_profile_render.returncode, 0)
            preview = self.run_script(
                "render_cards.py", project_path, output, profile_path, "--allow-draft", "--cover-only"
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertTrue((output / "cover.png").is_file())

            confirmed_profile = self.run_script(
                "profile_registry.py", "confirm", "--root", profile_root, "--slug", "demo-style"
            )
            self.assertEqual(confirmed_profile.returncode, 0, confirmed_profile.stderr)
            blocked = self.run_script("render_cards.py", project_path, output, profile_path)
            self.assertNotEqual(blocked.returncode, 0)
            cover_confirmed = self.run_script("project.py", "confirm-cover", project_path)
            self.assertEqual(cover_confirmed.returncode, 0, cover_confirmed.stderr)
            rendered = self.run_script("render_cards.py", project_path, output, profile_path)
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            for filename in ("cover.png", "card-01.png"):
                with Image.open(output / filename) as image:
                    self.assertEqual(image.size, (1080, 1440))

            publish_copy = article / "publish-copy.md"
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
            checked = self.run_script("validate_output.py", project_path, output, publish_copy)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            archive = article / "delivery.zip"
            packaged = self.run_script(
                "package_output.py", project_path, output, publish_copy, archive
            )
            self.assertEqual(packaged.returncode, 0, packaged.stderr)
            with zipfile.ZipFile(archive) as bundle:
                self.assertIn("output/card-01.png", bundle.namelist())
                self.assertIn("assets/article-images/image-01.png", bundle.namelist())

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
