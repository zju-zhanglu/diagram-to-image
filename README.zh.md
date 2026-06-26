# Diagram to Image

[English](README.md)

`diagram-to-image` 是一个 Agent Skill，用于把 Markdown 中的 ASCII 或 Unicode 文本图转换成忠实的 [draw.io](http://draw.io) PNG 图片。它会提取候选图块、分类、让用户选择要处理的图、生成 [draw.io](http://draw.io) XML、执行本地 XML 检查，并通过 [draw.io](http://draw.io) MCP 导出 PNG。

## 前置依赖

必须先安装并启用 [DayuanJiang/next-ai-draw-io](https://github.com/DayuanJiang/next-ai-draw-io/) 提供的 [draw.io](http://draw.io) MCP server。没有这个 MCP server，skill 仍可提取图块和检查 XML，但不能打开 [draw.io](http://draw.io) 会话或导出 PNG。

上游 README 给出的 MCP 配置示例：

```json
{
  "mcpServers": {
    "drawio": {
      "command": "npx",
      "args": ["@next-ai-drawio/mcp-server@latest"]
    }
  }
}
```

Claude Code CLI 示例：

```bash
claude mcp add drawio -- npx @next-ai-drawio/mcp-server@latest
```

还需要：

- Python 3，用于本地提取和 lint 脚本。
- 可用的 Agent 运行时，例如 Codex 或 Claude Code。

## 安装

### 一键安装（推荐）

```bash
npx @zju-zhanglu/diagram-to-image
```

交互式向导会引导你完成两个选择：

1. **选择 Agent** — 安装到哪些 Agent 运行时（Codex、Claude Code 或全部）。
2. **选择范围** — 安装到全局（所有项目可用）还是当前项目。

### 非交互安装

```bash
# 安装到所有 Agent，全局范围（默认）
npx @zju-zhanglu/diagram-to-image install --all

# 安装到指定 Agent
npx @zju-zhanglu/diagram-to-image install --agent codex --agent claude-code

# 安装到当前项目
npx @zju-zhanglu/diagram-to-image install --all --scope project
```

### 通过环境变量自动化

```bash
DIAGRAM_TO_IMAGE_AGENTS=codex,claude-code DIAGRAM_TO_IMAGE_SCOPE=global \
  npm install -g @zju-zhanglu/diagram-to-image

DIAGRAM_TO_IMAGE_AGENTS=all DIAGRAM_TO_IMAGE_SCOPE=project \
  npm install @zju-zhanglu/diagram-to-image
```

### 支持的 Agent

- `codex`
- `claude-code`

### 安装范围

| 范围 | Codex 路径 | Claude Code 路径 |
| --- | --- | --- |
| `global`（默认） | `$CODEX_HOME/skills/diagram-to-image` 或 `~/.codex/skills/diagram-to-image` | `$CLAUDE_HOME/skills/diagram-to-image` 或 `~/.claude/skills/diagram-to-image` |
| `project` | `./.codex/skills/diagram-to-image` | `./.claude/skills/diagram-to-image` |

### 卸载

```bash
# 从所有 Agent、全局和项目范围卸载
npx @zju-zhanglu/diagram-to-image install

# 从指定 Agent 卸载
npx @zju-zhanglu/diagram-to-image install --agent codex

# 仅从项目范围卸载
npx @zju-zhanglu/diagram-to-image install --all --scope project
```

卸载会删除 Agent skills 路径下的 `diagram-to-image/` 目录。要卸载 npm 包本身，请使用 `npm uninstall -g @zju-zhanglu/diagram-to-image`。

## 使用方式

在支持 skill 的 Agent 中调用：

```text
/diagram-to-image 转换 @/absolute/path/to/doc.md
```

如果希望跳过人工审核，必须在原始请求中明确说明，例如：

```text
/diagram-to-image 转换 @/absolute/path/to/doc.md ，并跳过人工审核。
```

## 工作流

1. 从 Markdown 中提取候选图块。
2. 将候选图分类为 `architecture`、`flowchart` 或 `sequence`。
3. 展示候选图列表，并等待用户选择要处理的图。
4. 为每个选中的图生成单页 [draw.io](http://draw.io) XML。
5. 按 `references/xml-review-checklist.md` 检查 XML。
6. 运行 `scripts/lint_drawio_xml.py`。
7. 通过 [draw.io](http://draw.io) MCP 打开图、等待人工审核或显式跳过审核，然后导出 PNG。
8. 返回 PNG 路径和验证摘要。

默认输出目录位于输入 Markdown 文件旁边：

```text
INPUT_DIR/
└── diagram-images/
    ├── diagram-blocks.json
    ├── diagram-001.xml
    └── diagram-001.png
```

## 质量要求

- 保留原图中的重要标签、层级和关系。
- 架构图必须保留真实容器层级，不能把嵌套结构拍平成无关卡片。
- 所有矩形使用轻微圆角：`rounded=1;arcSize=1`。
- 中文标签默认使用 `PingFang SC`。
- 字号默认不低于 13px。
- 画布应紧凑，不应有裁切或大面积空白。
- 连接线不能穿过关键文字或形状。

详细规则见：

- `SKILL.md`
- `references/architecture-layout-algorithm.md`
- `references/xml-review-checklist.md`

## License

MIT. See `LICENSE`.
