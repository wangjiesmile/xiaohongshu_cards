# 卡片项目数据格式

`cards.json` 使用 UTF-8 JSON。封面和内页分开，封面作者从已确认 profile 读取。

```json
{
  "version": 1,
  "seriesTitle": "文章短标题",
  "handle": "@账号",
  "cover": {
    "title": "封面标题",
    "illustration": "cover-illustration.png",
    "status": "confirmed"
  },
  "cards": [
    {
      "kind": "content",
      "eyebrow": "01 · 核心定义",
      "title": "每页只说明一个结论",
      "blocks": [
        {"kind": "paragraph", "text": "普通正文。"},
        {"kind": "highlight", "text": "重点结论。"},
        {"kind": "section", "text": "小节标题"},
        {"kind": "item", "number": "01", "title": "条目标题", "body": "条目说明。"},
        {"kind": "bullet", "text": "并列要点。"},
        {"kind": "code", "text": "命令或固定格式"},
        {"kind": "image", "path": "assets/article-images/image-01.png", "caption": "准确图注", "height": 360},
        {"kind": "note", "text": "提醒或边界。"},
        {"kind": "spacer", "height": 20}
      ]
    }
  ]
}
```

封面初建时 `status` 为 `draft`，确认后由 `project.py confirm-cover` 改为 `confirmed`。正式渲染必须同时满足：profile 已确认、封面已确认、`cards` 非空。

相对图片路径以 `cards.json` 所在目录为基准。每页至少包含一个 block，默认最多一张图片。图片高度范围为 220–520，spacer 高度范围为 8–80。超出页面时拆页，不忽略渲染错误。
