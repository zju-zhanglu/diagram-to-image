# Diagram to Image

[English](README.md)

`diagram-to-image` 是一个 Agent Skill，用于把 Markdown 中的 ASCII 或 Unicode 文本图转换成忠实的 draw.io PNG 图片。它会提取候选图块、分类、让用户选择要处理的图、生成 draw.io XML、执行本地 XML 检查，并通过 draw.io MCP 导出 PNG。

最终输出必须是由 draw.io 形状、容器、标签和连接线重建的图形。不要把原始文本图截图、渲染成 `<pre>`，或逐行摆成文本单元格。

## 前置依赖

必须先安装并启用 [DayuanJiang/next-ai-draw-io](https://github.com/DayuanJiang/next-ai-draw-io/) 提供的 draw.io MCP server。没有这个 MCP server，skill 仍可提取图块和检查 XML，但不能打开 draw.io 会话或导出 PNG。

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

- Python 3，用于本地提取、lint 和视觉模型选择脚本。
- 可用的 Agent 运行时，例如 Codex 或 Claude Code。
- 若要执行自动视觉复核，需要当前运行时中存在可处理图片输入的模型；没有时流程会跳过该复核步骤并继续收尾。

## 安装

全局安装 npm 包：

```bash
npm install -g @zju-zhanglu/diagram-to-image
```

然后选择要安装到哪些 Agent 运行时：

```bash
diagram-to-image install
```

v1 支持的 Agent 目标：

- `codex`
- `claude-code`

也可以使用非交互方式安装：

```bash
diagram-to-image install --agent codex
diagram-to-image install --agent claude-code
diagram-to-image install --all
```

如果希望在 `npm install -g` 时自动安装到指定 Agent，可设置 `DIAGRAM_TO_IMAGE_AGENTS`：

```bash
DIAGRAM_TO_IMAGE_AGENTS=codex,claude-code npm install -g @zju-zhanglu/diagram-to-image
DIAGRAM_TO_IMAGE_AGENTS=all npm install -g @zju-zhanglu/diagram-to-image
```

如果没有设置 `DIAGRAM_TO_IMAGE_AGENTS`，npm install 不会复制文件到 Agent 目录，只安装 CLI 并提示：

```text
Run: diagram-to-image install
```

安装器会把 skill 复制到：

- Codex：`$CODEX_HOME/skills/diagram-to-image` 或 `~/.codex/skills/diagram-to-image`
- Claude Code：`$CLAUDE_HOME/skills/diagram-to-image` 或 `~/.claude/skills/diagram-to-image`

查看支持的目标和安装状态：

```bash
diagram-to-image list-agents
diagram-to-image status
```

也可以手动安装：把整个 `diagram-to-image/` 目录放到你的 Agent skill 目录，或放到已配置的 skill root 中。目录结构应保留为：

```text
diagram-to-image/
├── SKILL.md
├── README.md
├── README.zh.md
├── agents/
├── references/
└── scripts/
```

确认 MCP 工具名为 `drawio`。`agents/openai.yaml` 也声明了该 MCP 依赖：

```yaml
dependencies:
  tools:
    - type: "mcp"
      value: "drawio"
```

## 使用方式

在支持 skill 的 Agent 中调用：

```text
Use $diagram-to-image to convert /absolute/path/to/doc.md into draw.io PNG images.
```

如果希望跳过人工审核，必须在原始请求中明确说明，例如：

```text
Use $diagram-to-image to convert /absolute/path/to/doc.md and skip manual review.
```

或：

```text
使用 $diagram-to-image 转换 /absolute/path/to/doc.md，并跳过人工审核。
```

## 工作流

1. 从 Markdown 中提取候选图块。
2. 将候选图分类为 `architecture`、`flowchart` 或 `sequence`。
3. 展示候选图列表，并等待用户选择要处理的图。
4. 为每个选中的图生成单页 draw.io XML。
5. 按 `references/xml-review-checklist.md` 检查 XML。
6. 运行 `scripts/lint_drawio_xml.py`。
7. 通过 draw.io MCP 打开图、等待人工审核或显式跳过审核，然后导出 PNG。
8. 可用时运行自动视觉复核。
9. 返回 PNG 路径和验证摘要。

默认输出目录位于输入 Markdown 文件旁边：

```text
INPUT_DIR/
└── diagram-images/
    ├── diagram-blocks.json
    ├── diagram-001.xml
    └── diagram-001.png
```

## 本地脚本

通过 npm 安装后，全局 CLI 会调用包内 Python 脚本：

```bash
diagram-to-image extract /absolute/path/to/doc.md \
  --out /absolute/path/to/diagram-images/diagram-blocks.json

diagram-to-image lint /absolute/path/to/diagram-001.xml

diagram-to-image select-vision-model --runtime codex --current-model "$MODEL"
```

在源码 checkout 或已安装的 skill 目录中，也可以直接运行 Python 脚本。

提取 Markdown 图块：

```bash
python3 scripts/extract_markdown_diagrams.py /absolute/path/to/doc.md \
  --out /absolute/path/to/diagram-images/diagram-blocks.json
```

如需扫描 4 空格缩进代码块：

```bash
python3 scripts/extract_markdown_diagrams.py /absolute/path/to/doc.md \
  --include-indented \
  --out /absolute/path/to/diagram-images/diagram-blocks.json
```

检查 draw.io XML：

```bash
python3 scripts/lint_drawio_xml.py /absolute/path/to/diagram-001.xml
```

选择可用于视觉复核的模型：

```bash
python3 scripts/select_vision_model.py --runtime codex --current-model "$MODEL"
python3 scripts/select_vision_model.py --runtime claude --current-model "$MODEL"
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
- `references/visual-review-checklist.md`

## License

MIT. See `LICENSE`.
