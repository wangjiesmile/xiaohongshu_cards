# xiaohongshu_cards

把个人人物形象和 Markdown 长文整理成一套可发布的小红书知识卡片。

它不是一组固定模板，而是一条可复用的内容工作流：先确认人物档案，再拆解文章与关键图片，生成独立的 16:9 主题插图，最后输出 1080×1440 封面、编号内页和发布文案。

## 能做什么

- 保存并复用人物名称、参考图、动作和主题色；
- 检查 Markdown 标题层级、段落和图片引用；
- 收集指定的本地或远程图片；
- 使用结构化 `project.json` 渲染稳定尺寸的 PNG；
- 在交付前检查图片数量、尺寸和发布文案结构；
- 内容过多时明确报告溢出，提示拆页。

## 安装

把仓库目录放入 Codex Skills 目录，并安装 Python 依赖：

```bash
python3 -m pip install -r requirements.txt
```

Skill 名称为 `xiaohongshu-cards`。目录和 GitHub 仓库可以继续使用 `xiaohongshu_cards`。

## 使用方式

在 Codex 中提供人物图和文章，例如：

```text
使用 $xiaohongshu-cards，把这份 Markdown 做成一套小红书知识卡片。
人物名称是「小王」，主题色 #2F6B5F，动作是站在白板前讲解。
```

完整流程及命令见 [SKILL.md](SKILL.md)，项目数据格式见 [references/project-schema.md](references/project-schema.md)。

## 输出

默认交付内容包括：

```text
cover.png
page-01.png
page-02.png
project.json
publish-copy.md
```

封面不编号，内页从 `01` 开始。封面数据采用 `title + illustration`：`title` 是单独排版的标题，`illustration` 是不含标题文字的 16:9 主题插图。这两部分由渲染器组合，不需要把标题提前画进插图。

## 设计原则

- 每页只表达一个主要结论；
- 教程截图和解释保持在同一页；
- 不虚构数据、经历或效果；
- 图片和人物素材保存在运行目录，不写入 Skill 安装目录；
- 默认拒绝内网图片地址、跳转响应和超大远程文件。

## 校验

```bash
python3 scripts/render.py --check
python3 -m unittest discover -s tests -v
```

## License

MIT
