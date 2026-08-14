# 人物与卡片样式注册表

## 人物目录

```text
.xiaohongshu-character-assets/
├── current-character.json
└── characters/<slug>/
    ├── character.json
    ├── character-sheet.png
    ├── character-reference-clean.png
    └── character-spec.md
```

人物状态只有 `draft` 和 `confirmed`。重新注册相同 slug 时增加 `revision`，新资产使用 `-v2`、`-v3` 等名称，旧文件不覆盖。确认人物会同时把它设为当前人物。只有已确认人物才能建立卡片样式。

## 样式目录

```text
.xiaohongshu-card-profiles/
├── current-profile.json
└── profiles/<slug>/
    ├── profile.json
    ├── character-sheet.png
    ├── character-clean.png
    ├── character-card-pose.png
    ├── character-spec.md
    ├── theme.json
    └── layout-sample.png
```

样式记录 `author_name`、`card_action`、主题和人物资产快照。`author_name` 只能来自人物确认阶段。重新注册会创建新 revision；确认后设为当前样式。

两种注册表都支持：

```bash
python3 scripts/<registry>.py resolve --root <root>
python3 scripts/<registry>.py resolve --root <root> --slug <slug> --allow-draft
python3 scripts/<registry>.py activate --root <root> --slug <slug>
python3 scripts/<registry>.py list --root <root>
```

运行资产不得保存到 Skill 安装目录或提交到代码仓库。
