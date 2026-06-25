# Diagram to Image

[中文](README.zh.md)

`diagram-to-image` is an Agent Skill that converts ASCII or Unicode text diagrams in Markdown into faithful [draw.io](http://draw.io) PNG images. It extracts candidate diagram blocks, classifies them, asks the user which diagrams to process, generates [draw.io](http://draw.io) XML, runs local XML checks, and exports PNGs through the [draw.io](http://draw.io) MCP server.

The final output must be a graphical reconstruction made of [draw.io](http://draw.io) shapes, containers, labels, and connectors. Do not satisfy the task by screenshotting the original text diagram, rendering it as `<pre>`, or placing each source line into text cells.

## Prerequisite

Install and enable the [draw.io](http://draw.io) MCP server from [DayuanJiang/next-ai-draw-io](https://github.com/DayuanJiang/next-ai-draw-io/) before using this skill. Without that MCP server, the skill can still extract diagram blocks and lint XML, but it cannot open a [draw.io](http://draw.io) session or export PNG files.

MCP configuration example from the upstream README:

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

Claude Code CLI example:

```bash
claude mcp add drawio -- npx @next-ai-drawio/mcp-server@latest
```

You also need:

- Python 3 for local extraction, linting, and vision-model selection scripts.
- An Agent runtime such as Codex or Claude Code.
- An image-capable model if you want automated visual review. If none is available, the workflow records that visual review was skipped and continues.

## Installation

### One-command install (recommended)

```bash
npx @zju-zhanglu/diagram-to-image
```

The interactive wizard walks you through two choices:

1. **Agent selection** — which Agent runtimes to install to (Codex, Claude Code, or all).
2. **Scope** — install globally (available in all projects) or to the current project only.

### Non-interactive install

```bash
# Install to all agents, global scope (default)
npx @zju-zhanglu/diagram-to-image install --all

# Install to specific agents
npx @zju-zhanglu/diagram-to-image install --agent codex --agent claude-code

# Install to current project only
npx @zju-zhanglu/diagram-to-image install --all --scope project
```

### Automation via environment variables

```bash
DIAGRAM_TO_IMAGE_AGENTS=codex,claude-code DIAGRAM_TO_IMAGE_SCOPE=global \
  npm install -g @zju-zhanglu/diagram-to-image

DIAGRAM_TO_IMAGE_AGENTS=all DIAGRAM_TO_IMAGE_SCOPE=project \
  npm install @zju-zhanglu/diagram-to-image
```

### Supported agents

- `codex`
- `claude-code`

### Install scopes

| Scope | Codex path | Claude Code path |
| --- | --- | --- |
| `global` (default) | `$CODEX_HOME/skills/diagram-to-image` or `~/.codex/skills/diagram-to-image` | `$CLAUDE_HOME/skills/diagram-to-image` or `~/.claude/skills/diagram-to-image` |
| `project` | `./.codex/skills/diagram-to-image` | `./.claude/skills/diagram-to-image` |

### Check status

```bash
diagram-to-image list-agents
diagram-to-image status
```

### Uninstall

```bash
# Remove from all agents, both global and project
diagram-to-image uninstall

# Remove from specific agents
diagram-to-image uninstall --agent codex

# Remove only from project scope
diagram-to-image uninstall --all --scope project
```

Uninstall removes the `diagram-to-image/` directory from the agent skills path. It does NOT uninstall the npm package — use `npm uninstall -g @zju-zhanglu/diagram-to-image` for that.

### Manual installation

Place the whole `diagram-to-image/` directory in your Agent skills directory or any configured skill root. Keep this structure intact:

```text
diagram-to-image/
├── SKILL.md
├── README.md
├── README.zh.md
├── agents/
├── references/
└── scripts/
```

Make sure the MCP tool is named `drawio`. `agents/openai.yaml` declares the same dependency:

```yaml
dependencies:
  tools:
    - type: "mcp"
      value: "drawio"
```

## Usage

In a skill-aware Agent, ask:

```text
Use $diagram-to-image to convert /absolute/path/to/doc.md into draw.io PNG images.
```

To skip manual review, the original request must say so explicitly:

```text
Use $diagram-to-image to convert /absolute/path/to/doc.md and skip manual review.
```

## Workflow

1. Extract candidate diagram blocks from Markdown.
2. Classify each candidate as `architecture`, `flowchart`, or `sequence`.
3. Show the candidates and wait for the user to choose which diagrams to process.
4. Generate one-page [draw.io](http://draw.io) XML for each selected diagram.
5. Review XML with `references/xml-review-checklist.md`.
6. Run `scripts/lint_drawio_xml.py`.
7. Open the diagram through the [draw.io](http://draw.io) MCP server, wait for manual approval or an explicit bypass, then export PNG.
8. Run automated visual review when available.
9. Return PNG paths and a short verification summary.

By default, outputs are written beside the input Markdown file:

```text
INPUT_DIR/
└── diagram-images/
    ├── diagram-blocks.json
    ├── diagram-001.xml
    └── diagram-001.png
```

## Local Scripts

When installed with npm, the global CLI delegates to the bundled Python scripts:

```bash
diagram-to-image extract /absolute/path/to/doc.md \
  --out /absolute/path/to/diagram-images/diagram-blocks.json

diagram-to-image lint /absolute/path/to/diagram-001.xml

diagram-to-image select-vision-model --runtime codex --current-model "$MODEL"
```

From a source checkout or installed skill directory, you can also run the Python scripts directly.

Extract Markdown diagram blocks:

```bash
python3 scripts/extract_markdown_diagrams.py /absolute/path/to/doc.md \
  --out /absolute/path/to/diagram-images/diagram-blocks.json
```

Include 4-space indented code blocks:

```bash
python3 scripts/extract_markdown_diagrams.py /absolute/path/to/doc.md \
  --include-indented \
  --out /absolute/path/to/diagram-images/diagram-blocks.json
```

Lint [draw.io](http://draw.io) XML:

```bash
python3 scripts/lint_drawio_xml.py /absolute/path/to/diagram-001.xml
```

Select a model for visual review:

```bash
python3 scripts/select_vision_model.py --runtime codex --current-model "$MODEL"
python3 scripts/select_vision_model.py --runtime claude --current-model "$MODEL"
```

## Quality Bar

- Preserve important labels, hierarchy, and relationships from the source.
- Architecture diagrams must keep real container hierarchy; do not flatten nested structures into unrelated cards.
- Use light rounded rectangles: `rounded=1;arcSize=1`.
- Use `PingFang SC` for Chinese labels by default.
- Keep default text at 13px or larger.
- Keep the canvas tight, without clipping or large blank margins.
- Route connectors away from important text and shapes.

See the detailed rules in:

- `SKILL.md`
- `references/architecture-layout-algorithm.md`
- `references/xml-review-checklist.md`
- `references/visual-review-checklist.md`

## License

MIT. See `LICENSE`.