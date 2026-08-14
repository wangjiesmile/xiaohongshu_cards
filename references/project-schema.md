# 项目数据格式

`project.json` 使用 UTF-8 JSON：

```json
{
  "version": 1,
  "cover": {
    "title": "封面标题",
    "illustration": "cover-illustration.png"
  },
  "pages": [
    {
      "kicker": "核心方法",
      "title": "每页只说明一个结论",
      "blocks": [
        {"type": "paragraph", "text": "正文"},
        {"type": "highlight", "text": "重点结论"},
        {"type": "bullet", "text": "并列要点"},
        {"type": "code", "text": "命令或固定格式"},
        {"type": "image", "path": "assets/image-01.png", "caption": "准确图注"}
      ]
    }
  ]
}
```

相对图片路径以 `project.json` 所在目录为基准。封面作者和人物图从已确认 `profile.json` 读取，不写入文章项目。

页面至少包含一个内容块。块类型只允许 `paragraph`、`highlight`、`bullet`、`code` 和 `image`。图片图注来自原文 alt、相邻说明或明确语境，不猜测不可辨认内容。
