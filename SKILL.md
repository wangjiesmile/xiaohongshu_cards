---
name: xiaohongshu-cards
description: 将个人照片或现成人物 IP 与 Markdown 长文整理成可直接发布的小红书知识卡片。建立可复用人物档案和主题色，识别文章结构与关键截图，生成主题插图、1080x1440 封面、编号内页、发布标题、正文和话题。用户要求长文转小红书图文、个人 IP 卡片、Markdown 转图片、保留教程截图或点名 $xiaohongshu-cards 时使用。
---

# Xiaohongshu Cards

把人物确认、内容拆分、视觉生成和交付检查作为一条连续流程执行。不要在人物或视觉样式未确认时批量制作文章卡片。

## 首次响应

没有已确认人物档案时，只索取以下信息：

1. 清晰人物照片或现成人物 IP 图；
2. 人物名称，即封面作者名；
3. 主题色 Hex 值，可留空；
4. 人物在卡片中的动作。

用户没有主题色时，从服装或稳定配件提出一个候选色。用户没有动作时，提供三个与知识讲解有关的候选动作。取得明确确认后再进入文章阶段。

## 阶段判断

- 没有人物档案：创建人物草稿。
- 人物状态为 `draft`：展示人物图、名称、动作和颜色，只处理修改或确认。
- 人物已确认但没有文章：请用户提供完整 Markdown。
- 收到文章：解析全文和图片，拟定卡片结构与封面标题。
- 封面未确认：只生成或修订封面。
- 封面已确认：生成内页、发布文案、校验并打包。

## 建立人物档案

读取 `references/persona.md`。使用图像生成工具创建干净人物参考图时，只从用户素材提取可观察的外貌、服装和配件，不推断敏感属性。

使用脚本登记人物：

```bash
python3 scripts/profile.py create \
  --root <runtime-profile-root> \
  --slug <profile-slug> \
  --name <人物名称> \
  --accent '#2F6B5F' \
  --action <人物动作> \
  --character <人物图绝对路径>
```

只有用户明确确认时运行：

```bash
python3 scripts/profile.py confirm --root <runtime-profile-root> --slug <profile-slug>
```

人物照片、档案和文章素材不得写入 Skill 安装目录。

## 读取文章

读取 `references/content-planning.md`，并运行：

```bash
python3 scripts/inspect_markdown.py <source.md> --output <analysis.json>
```

完整检查解析结果中的标题、章节和图片。作者名只来自已确认人物档案，不采用 Markdown 的 `author` 字段或署名段落。

选择图片时优先保留教程操作、流程关系、数据证据、前后对比和完成结果。装饰头图、头像、重复封面和无关 Logo 不进入正文。

## 生成封面插图

读取 `references/illustration.md`。从文章中选择一个最能代表全文的画面命题，生成一张 16:9 插图。人物必须参与核心动作，并保持人物档案中的脸、发型、体型、服装和配件。

插图不得包含封面标题、作者、账号、Logo 或页码。将确认使用的文件保存为文章目录下的 `cover-illustration.png`。

## 组织卡片数据

读取 `references/project-schema.md`，创建 `project.json`。

- 封面只保存标题与插图路径。
- 正文页从 `01` 开始编号。
- 一页只表达一个主要结论。
- 默认每页最多一张关键图。
- 文字过多时增加页数，不缩小到不可读。
- 不新增原文没有的数据、经历、能力或承诺。

远程或本地文章图片通过以下命令收集：

```bash
python3 scripts/collect_images.py <analysis.json> <assets-dir> --indexes 1,2,3
```

## 渲染与确认

先检查运行环境：

```bash
python3 scripts/render.py --check
```

再渲染：

```bash
python3 scripts/render.py <project.json> <profile.json> <output-dir>
```

逐张检查标题、正文、截图、人物比例和页码。内容溢出时重新拆页，不忽略渲染错误。

## 发布文案

生成 `publish-copy.md`，必须包含：

- `## 推荐标题`：一个标题；
- `## 备选标题`：三个标题；
- `## 正文`：自然中文正文；
- `## 话题`：六至十个相关话题。

标题把搜索词放在前半句，不使用无法证明的夸张结果。正文不得伪造作者经历。

## 最终验收

运行：

```bash
python3 scripts/validate.py <project.json> <output-dir> <publish-copy.md>
```

通过后打包文章目录。默认交付一个无页码封面、若干从 `01` 开始的内页、结构化项目数据、发布文案和 ZIP。

没有图像生成能力时，输出完整插图提示词、人物参考路径和保存计划，并明确说明插图尚未生成。
