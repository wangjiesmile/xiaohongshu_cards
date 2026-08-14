---
name: xiaohongshu-cards
description: 从人物照片或现成人物 IP 建立并确认可复用人物资产、作者名、动作和主题色，再把包含文字、截图、图表或流程图的 Markdown 长文制作成 1080x1440 小红书知识卡片。执行人物确认、卡片样式确认和封面确认三道门，保留理解文章不可缺少的关键图，并输出封面、编号内页、发布标题、正文、话题和 ZIP。用户要求上传照片生成个人 IP、个人 IP 知识卡片、Markdown 转小红书图、保留教程截图、先确认封面再做内页或点名 $xiaohongshu-cards 时使用。
---

# Xiaohongshu Cards

依次执行人物确认、卡片样式确认、封面确认。前一阶段未确认时停止，不提前生产后一阶段内容。人物参考图是必需输入；当前流程不支持无人物卡片。

## 首次使用

没有已确认人物时，不读取文章，只发送以下引导：

```text
先建立你的个人 IP 和卡片视觉样式。请准备：
1. 一张清晰人物照片，或一张已经完成的人物 IP 图；
2. 人物名称或昵称，它会作为封面作者名；
3. 一个主题色 Hex 值或颜色参考，可以暂时不填；
4. 希望人物在卡片里完成的动作。

人物和样式确认后，我再读取 Markdown。封面会单独生成并请你确认，确认后才制作内页和发布文案。
```

没有主题色时，从服装或稳定配件提出一个候选色。没有动作时，提供三个与文章讲解有关的候选动作并标出推荐项。

## 每次开始

1. 用 `character_registry.py resolve` 检查当前人物；没有当前人物时进入人物阶段。
2. 用 `profile_registry.py resolve` 检查当前卡片样式；没有当前样式时进入样式阶段。
3. 用 `project.py status` 检查当前文章封面状态。
4. 不把用户照片、人物资产、文章或生成插图写入 Skill 安装目录。

运行数据默认放在项目目录：

```text
<project-root>/.xiaohongshu-character-assets/
<project-root>/.xiaohongshu-card-profiles/
```

## 第一门：人物确认

读取 `references/persona.md`、`references/character-generation.md` 和 `references/registries.md`。

### 从照片建立人物

1. 以用户照片为唯一身份来源，只提取可观察的脸、发型、体型、服装和配件。
2. 生成角色设定板、干净人物参考图和 `character-spec.md`。
3. 不推断职业、民族、健康、政治、宗教或其他敏感属性。
4. 注册人物草稿：

```bash
python3 scripts/character_registry.py register \
  --root <character-root> \
  --slug <character-slug> \
  --name <人物名称> \
  --theme-color '#2F6B5F' \
  --sheet <设定板路径> \
  --clean-reference <干净人物图路径> \
  --spec <character-spec.md路径>
```

`--theme-color` 可省略。展示人物结果，只询问确认或修改。用户明确说“确认”“定稿”或“就用这个”后运行：

```bash
python3 scripts/character_registry.py confirm --root <character-root> --slug <character-slug>
```

人物每次重新注册都会增加 revision 并保留旧资产。草稿人物不能进入样式阶段。

## 第二门：卡片样式确认

读取 `references/registries.md`、`references/character-generation.md` 和 `references/illustration.md`。

1. 从已确认人物生成一张卡片动作图，保持身份、服装、配件和自然比例。
2. 使用用户主题色；没有指定时从人物图生成候选主题：

```bash
python3 scripts/derive_palette.py \
  --image <人物图路径> \
  --out <theme.json> \
  --profile-name <人物名称> \
  --handle <账号，可省略> \
  --accent '#2F6B5F'
```

3. 在读取文章前生成正文样稿：

```bash
python3 scripts/style_preview.py \
  --theme <theme.json路径> \
  --card-pose <卡片动作图路径> \
  --author-name <人物名称> \
  --action <确认的卡片动作> \
  --output <layout-sample.png>
```

4. 注册卡片样式草稿：

```bash
python3 scripts/profile_registry.py register \
  --root <profile-root> \
  --slug <profile-slug> \
  --name <样式名称> \
  --author-name <人物阶段确认的名称> \
  --action <确认的卡片动作> \
  --sheet <设定板路径> \
  --clean-reference <干净人物图路径> \
  --card-pose <卡片动作图路径> \
  --spec <character-spec.md路径> \
  --theme <theme.json路径> \
  --layout-sample <layout-sample.png路径>
```

5. 展示动作图、主题色和正文样稿，只询问确认或修改。
6. 用户明确确认后运行：

```bash
python3 scripts/profile_registry.py confirm --root <profile-root> --slug <profile-slug>
```

草稿样式只能渲染样稿，不能正式生产文章内页。

## 读取 Markdown

读取 `references/content-planning.md`，运行：

```bash
python3 scripts/parse_markdown.py <source.md> --output <analysis.json> --write-clean <article-dir>/source.md
```

1. 标题优先读取 YAML `title`，其次读取第一个一级标题。
2. 作者名只读取已确认 profile 的 `author_name`，不采用 Markdown 署名。
3. 结合全文检查图片的前后文与 `selection_hint`；提示只用于初筛。
4. 保留操作位置、流程关系、数据证据、前后对比和完成结果；跳过头像、Logo、重复封面与装饰图。
5. 教程文章先建立“步骤—截图—完成标志”映射，必需截图不能省略。

收集选中的图片：

```bash
python3 scripts/collect_markdown_images.py \
  <source.md> <article-dir>/assets/article-images \
  --indexes 1,2,3
```

## 第三门：封面确认

读取 `references/illustration.md` 和 `references/project-schema.md`。

1. 从全文选择一个认知锚点，生成一张 16:9 人物主题插图。人物参与核心动作并保持已确认身份。
2. 插图不包含大标题、作者、账号、Logo 或页码，保存为 `cover-illustration.png`。
3. 建立封面草稿：

```bash
python3 scripts/project.py create \
  --output <article-dir>/cards.json \
  --series-title <文章短标题> \
  --title <封面标题> \
  --illustration cover-illustration.png \
  --handle <账号，可省略>
```

4. 渲染封面样稿：

```bash
python3 scripts/render_cards.py \
  <cards.json> <output-dir> <profile.json> \
  --cover-only
```

5. 展示主题插图、最终封面、作者名和主题色，只询问确认或修改。
6. 用户明确确认后运行：

```bash
python3 scripts/project.py confirm-cover <cards.json>
```

封面未确认时，正式渲染命令必须失败。

## 制作内页

按 `references/project-schema.md` 向 `cards.json` 添加 `cards`。遵守以下规则：

- 封面不编号，内页从 `01` 开始；
- 默认一张封面加九张内页，可根据内容增减，不重复凑页；
- 每页表达一个主要结论，建议四至八个 blocks；
- 默认每页最多一张关键图，图片与解释同页；
- 文字过多时增加页数，不缩小到不可读；
- 不新增原文没有的数据、经历、结论或承诺。

正式渲染：

```bash
python3 scripts/render_cards.py <cards.json> <output-dir> <profile.json>
```

macOS 与 Linux 可使用 `scripts/render_cards.sh`，Windows 可使用 `scripts/render_cards.ps1`；三个入口调用同一个 Python 渲染器。

逐张检查标题、正文、截图、人物比例、页码、截断与重叠。内容溢出时重新拆页。

## 发布文案

生成 `publish-copy.md`：

- `## 推荐标题`：一个标题；
- `## 备选标题`：三个标题；
- `## 正文`：自然中文正文；
- `## 话题`：六至十个相关话题。

标题把搜索词放在前半句，不使用无法证明的夸张结果。正文不伪造作者经历。

## 验收与打包

```bash
python3 scripts/validate_output.py <cards.json> <output-dir> <publish-copy.md>

python3 scripts/package_output.py \
  <cards.json> <output-dir> <publish-copy.md> <delivery.zip>
```

校验必须确认：封面已确认、PNG 数量正确、全部图片为 1080×1440、选中的关键图全部进入卡片、发布文案完整。通过后交付 `cover.png`、`card-01.png ...`、项目数据、发布文案和 ZIP。

没有图像生成能力时，输出人物或封面插图的完整提示词、身份参考路径和保存计划，并明确说明当前停在哪一道确认门。
