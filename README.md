# xiaohongshu_cards

把人物照片或现成人物 IP 与 Markdown 长文制作成可直接发布的小红书知识卡片。

项目提供完整的三阶段确认流程：先确认人物身份，再确认卡片动作与主题色，最后确认文章封面。只有三道确认门全部通过，才能正式生成编号内页、发布文案和 ZIP。

## 功能

- 从人物照片或现成人物 IP 建立可复用人物资产；
- 保存人物名称、作者名、动作、主题色及历史 revision；
- 创建、确认、切换多个卡片样式；
- 解析 Markdown 标题、层级、Markdown 图片和 HTML 图片；
- 根据图片上下文提供 `keep / review / skip` 初筛提示；
- 安全收集本地或远程关键图，并检查它们是否进入内页；
- 分别生成和确认 16:9 主题插图封面；
- 渲染 1080×1440 的无页码封面和编号内页；
- 支持段落、重点、小节、步骤、项目符号、代码、图片、提醒和留白块；
- 检查内容溢出、图片数量、尺寸、发布文案和关键图完整性；
- 打包完整交付 ZIP。

## 安装

```bash
python3 -m pip install -r requirements.txt
```

把仓库放入 Codex Skills 目录，Skill 名称使用 `xiaohongshu-cards`。

## 使用

```text
使用 $xiaohongshu-cards，把我的人物照片和 Markdown 文章制作成一套小红书知识卡片。
```

首次使用需要准备：人物照片或现成 IP 图、人物名称、主题色和卡片动作。主题色与动作暂时没有想法时，可以由 Skill 提供候选方案。

完整执行流程见 [SKILL.md](SKILL.md)，数据格式见 [references/project-schema.md](references/project-schema.md)。

## 输出

```text
<article>/
├── source.md
├── cover-illustration.png
├── cards.json
├── publish-copy.md
├── assets/article-images/
│   ├── image-01.png
│   └── manifest.json
├── output/
│   ├── cover.png
│   ├── card-01.png
│   └── card-02.png
└── delivery.zip
```

封面不编号，内页从 `01` 开始。封面数据使用 `title + illustration + status`：标题和 16:9 插图分开保存，确认后 `status` 变为 `confirmed`。

## 检查

```bash
python3 scripts/render_cards.py --check
python3 -m unittest discover -s tests -v
```

macOS 与 Linux 也可使用 `scripts/render_cards.sh`，Windows 可使用 `scripts/render_cards.ps1`；所有入口调用同一个 Python 渲染器。

远程图片默认拒绝内网地址、非标准端口、凭据 URL、跳转响应和超过体积限制的文件。

## License

MIT
