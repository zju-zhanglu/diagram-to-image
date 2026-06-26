# Diagram to Image

[中文](README.zh.md)

`diagram-to-image` is an Agent Skill that converts ASCII or Unicode text diagrams in Markdown into faithful [draw.io](http://draw.io) PNG images. It extracts candidate diagram blocks, classifies them, asks the user which diagrams to process, generates [draw.io](http://draw.io) XML, runs local XML checks, and exports PNGs through the [draw.io](http://draw.io) MCP server.

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

- Python 3 for local extraction and linting scripts.
- An Agent runtime such as Codex or Claude Code.

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

### Uninstall

```bash
# Remove from all agents, both global and project
npx @zju-zhanglu/diagram-to-image uninstall

# Remove from specific agents
npx @zju-zhanglu/diagram-to-image uninstall --agent codex

# Remove only from project scope
npx @zju-zhanglu/diagram-to-image uninstall --all --scope project
```

Uninstall removes the `diagram-to-image/` directory from the agent skills path. It does NOT uninstall the npm package — use `npm uninstall -g @zju-zhanglu/diagram-to-image` for that.

## Usage

In a skill-aware Agent, ask:

```text
/diagram-to-image convert @/absolute/path/to/doc.md
```

To skip manual review, the original request must say so explicitly:

```text
/diagram-to-image convert @/absolute/path/to/doc.md and skip manual review.
```

## Workflow

1. Extract candidate diagram blocks from Markdown.
2. Classify each candidate as `architecture`, `flowchart`, or `sequence`.
3. Show the candidates and wait for the user to choose which diagrams to process.
4. Generate one-page [draw.io](http://draw.io) XML for each selected diagram.
5. Review XML with `references/xml-review-checklist.md`.
6. Run `scripts/lint_drawio_xml.py`.
7. Open the diagram through the [draw.io](http://draw.io) MCP server, wait for manual approval or an explicit bypass, then export PNG.
8. Return PNG paths and a short verification summary.

By default, outputs are written beside the input Markdown file:

```text
INPUT_DIR/
└── diagram-images/
    ├── diagram-blocks.json
    ├── diagram-001.xml
    └── diagram-001.png
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

## License

MIT. See `LICENSE`.
