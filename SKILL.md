---
name: diagram-to-image
description: Convert Markdown documents containing ASCII or Unicode text diagrams into faithful draw.io PNG images. Use when the user provides a Markdown file or Markdown text and asks to extract architecture diagrams, flowcharts, or sequence diagrams from fenced or indented text blocks, generate draw.io XML through the drawio MCP, review and lint XML, gate export through browser-based human approval, and export PNGs.
---

# Diagram To Image

## Overview

Convert Markdown text diagrams into one PNG per selected diagram by extracting candidate code blocks, classifying them, asking the user which diagrams to process, generating single-diagram draw.io XML, reviewing and linting the XML, gating export through draw.io browser human approval, and exporting with the drawio MCP. Prioritize structural fidelity, correct containment, readable labels, and a tight canvas.

The final PNG must be a graphical reconstruction made of draw.io shapes, containers, labels, and connectors. Do not satisfy the task by rendering the original ASCII/Unicode block as a screenshot, `<pre>` block, line-by-line text cells, or any other raw text facsimile.

## Output Location

When the input is a Markdown file, write all generated artifacts under the input document's directory, not under the current working directory or the skill directory. Use this layout by default:

```text
INPUT_DIR/
└── diagram-images/
    ├── diagram-blocks.json
    ├── diagram-001.xml
    └── diagram-001.png
```

Use `diagram-images/` unless the user explicitly requests another folder. For pasted Markdown without a source file, first save or treat the Markdown in a user-appropriate working document location, then place `diagram-images/` beside that input document. Include absolute output paths in the final summary.

## Workflow State Tracking

Before starting Step 1, create a visible task list for the Required Workflow. Include Steps 1-8 and initialize every item as `PENDING`. Use only these status values:

- `PENDING`
- `IN_PROGRESS`
- `DONE`
- `SKIPPED: reason`
- `BLOCKED: reason`
- `UNRESOLVED: reason`

Update the task list before starting a step, after finishing a step, and before moving to the next step. Do not claim completion while any selected diagram has a required item left as `PENDING`, `IN_PROGRESS`, or `BLOCKED`.

After Step 3, expand Steps 4-7 into per-diagram task items for every selected block id, such as `Step 4 / block-2: generate XML`, `Step 5 / block-2: XML review`, `Step 6 / block-2: lint`, and `Step 7 / block-2: approval and export`. Track each selected diagram separately through retries.

Mark skipped work only with a concrete reason. Valid examples include `SKIPPED: user selected no diagrams` or `SKIPPED: subagent tools unavailable; completed sequentially`. Mark a diagram `UNRESOLVED: reason` only after the allowed retries are exhausted or the user explicitly stops that diagram.

Before the final summary, audit the task list. Every Required Workflow item and every selected diagram's per-diagram item must be terminal: `DONE`, `SKIPPED: reason`, or `UNRESOLVED: reason`.

## Required Workflow

1. Extract candidate diagrams from the Markdown input:
   ```bash
   INPUT_MD=/absolute/path/to/INPUT.md
   INPUT_DIR=$(cd "$(dirname "$INPUT_MD")" && pwd)
   OUTPUT_DIR="$INPUT_DIR/diagram-images"
   mkdir -p "$OUTPUT_DIR"
   python3 scripts/extract_markdown_diagrams.py "$INPUT_MD" --out "$OUTPUT_DIR/diagram-blocks.json"
   ```
   Run the command from the skill directory, or adjust the script path relative to the current working directory.
   Inspect the JSON. If the script misses an obvious diagram, add it manually to the working set and keep the original Markdown as the source of truth.

2. Classify every extracted block as exactly one of:
   - `architecture`: container/layer/component diagrams, especially nested box drawings.
   - `flowchart`: process, decision, state, or pipeline flow.
   - `sequence`: actor/lifeline/message interaction over time.

3. Present the classification results to the user and ask which diagrams to process before generating XML:
   - List every candidate in source order with `id`, category, confidence if available, source lines, heading if available, and a short one-line content preview.
   - Offer choices that let the user select one diagram, several diagrams by id, or all diagrams.
   - Do not generate XML, create draw.io diagrams, or export PNGs until the user chooses the processing scope.
   - If the user selects none, stop and report that no diagrams were processed.
   - Treat the selected diagrams as the working set for all remaining steps.

4. Spawn one subagent per selected code block to generate draw.io XML. Give each subagent only the relevant code block, its classification, the output path, and the constraints in this skill. Put every XML file in `OUTPUT_DIR` beside the input document, using stable names such as `diagram-001.xml`. Require a single-page `mxGraphModel` or one-page `mxfile`; reject multi-page or multi-diagram XML.
   - Require graphical reconstruction. The source ASCII/Unicode borders are analysis input only; they must not appear as the main visual output.
   - For `architecture`, also give the subagent `references/architecture-layout-algorithm.md` and require the container tree, layout summary, and self-check before XML.

5. Spawn one subagent per XML file to review the XML before export. Use `references/xml-review-checklist.md` as the review rubric. Fix any blocking issue before calling drawio.

6. Run the local XML linter for each XML file after review fixes:
   ```bash
   python3 scripts/lint_drawio_xml.py OUTPUT.xml
   ```
   Treat errors as blocking. Warnings require a quick judgment call; fix warnings that affect hierarchy, readability, padding, or canvas tightness.

7. Export PNGs with the drawio MCP through a strict per-diagram human approval gate, unless the original user request explicitly asks to skip manual review:
   - Before processing the first diagram, set `manual_review_bypass=true` only when the original user request contains an explicit bypass phrase in Chinese or English, such as `跳过人工审查`, `跳过人工审核`, `跳过人工确认`, `skip manual review`, `skip human review`, `skip manual approval`, or `skip human approval`. Do not infer bypass from vague urgency or automation requests.
   - Process diagrams serially in source-block order. Do not parallelize drawio MCP create, browser review, user approval, or PNG export.
   - Start a drawio session if needed.
   - Call `create_new_diagram` with exactly one diagram's XML. Never send multiple pages or multiple diagrams in one XML payload.
   - If `manual_review_bypass=false`, show that one diagram to the user in the drawio browser page and explicitly ask the user to review it before exporting.
   - If `manual_review_bypass=true`, treat the human approval gate as automatically passed for that diagram, record the human approval outcome as `AUTO-PASSED: manual_review_bypass=true`, and continue directly to PNG export from the current drawio browser state.
   - If `manual_review_bypass=false`, let the user either approve or reject. These are the only two manual review outcomes:
     - **Pass**: the user approves the diagram. The user may approve it as-is or first adjust it directly in the browser page, then approve.
     - **Reject**: the user rejects the diagram. Do not export it. Return to XML generation for that same diagram, then repeat XML review, lint, browser display, and human approval for that diagram.
   - After approval or auto-pass, call `export_diagram` to write exactly one PNG from the current drawio browser state. The PNG output path must be under `OUTPUT_DIR` beside the input document, using the same stem as the XML, such as `diagram-001.png`.
   - Do not start the next diagram's drawio create/review/export cycle until the current diagram is either exported after user approval/auto-pass or reported as unresolved after 3 rejected generation attempts.
   - Retry at most 3 generation attempts per diagram, then report the unresolved failure clearly.

8. Return the PNG paths and a short verification summary listing the input document path, `OUTPUT_DIR`, each selected source block id, category, attempts, XML review status, lint status, and human approval outcome. Also note any extracted block ids the user did not select.

If subagent tools are unavailable in the current session, continue sequentially instead of pretending delegation happened, and state that limitation in the final summary.

## Extraction Script Output

`extract_markdown_diagrams.py` returns JSON with:

- `source`: input file path.
- `blocks`: extracted candidates with `id`, `category`, `confidence`, `start_line`, `end_line`, `heading`, `fence`, `reasons`, and `content`.
- `summary`: counts by category.

Treat the script's category as a first pass. Override it when the diagram semantics are clearer than the heuristic.

Classification precedence:

1. Obvious participants/lifelines with chronological messages -> `sequence`.
2. Obvious nested boxes, system boundaries, layers, modules, or many box-drawing borders -> `architecture`, even if arrows also appear.
3. States, steps, decisions, pipelines, or transitions without strong containment -> `flowchart`.

## Global Hard Constraints

- Use `rounded=1` and `arcSize=1` on every rectangular shape.
- Use readable fonts: child items 13-14px, titles 14-16px, never below 13px by default.
- Use `fontFamily=PingFang SC`; use `Microsoft YaHei` only when needed.
- Prefer single-line labels. For long text, enable wrapping and increase width and height.
- Size wrapped leaf nodes from estimated rendered line count: reserve roughly 18-22px per line plus 8-12px vertical padding, then recalculate the parent container height.
- After wrapping long labels, re-check the rendered height and parent bottom padding; wrapped text must not touch or exceed the parent container.
- Keep connectors away from important text and shapes. Use explicit `exitX`, `exitY`, `entryX`, `entryY`, and waypoints where needed.
- Keep the canvas compact: no large empty margins, no clipped content, and no off-canvas shapes.
- Preserve all important labels and relationships from the source block. Do not add domain-specific content that is not present or clearly implied.
- Reconstruct diagrams as graphical draw.io elements. Never render the original ASCII/Unicode block wholesale as the final image.
- Preserve hierarchy and grouping as visual containment. Do not flatten a nested/container diagram into an unrelated grid of cards unless the source itself is a flat list.

## Architecture Diagram Rules

Architecture diagrams are usually the most fragile. Complete structure analysis before writing XML.

For full layout procedure, read and apply `references/architecture-layout-algorithm.md`. The short rules below are mandatory reminders, not a replacement for that reference.

1. First produce a container tree:
   - root containers
   - parent containers
   - sibling container groups
   - leaf items

2. Compute layout recursively:
   - Calculate each container from its children outward.
   - Use only the parent container and same-level siblings when calculating a container's placement; do not depend on ancestors except when converting relative coordinates to absolute coordinates.
   - After inner-to-outer sizing, adjust outer-to-inner placement to satisfy containment, alignment, and centering.

3. Enforce containment:
   - Child containers must be fully inside the parent.
   - Children must not cross the parent border or title area.
   - The container tree must be reflected in real `mxCell parent` attributes. For architecture diagrams, use the semantic parent container id as each child container or leaf node's `parent`, and use coordinates relative to that parent.
   - Do not flatten nested architecture diagrams by placing all cells under `parent="1"` with absolute coordinates. Keep only true root-level containers under `parent="1"`.
   - Treat layout comments and self-check notes as documentation only. They do not prove containment unless the XML parent tree and rendered geometry match them.

4. Lay out sibling container groups:
   - Children under the same parent must not overlap.
   - Calculate the sibling group size first.
   - Center the sibling group inside the parent content area.
   - Treat leaf rectangles as terminal containers for architecture layout. Leaf-only groups must be compact content groups, not loose vertically centered lists inside oversized parents.
   - For vertically stacked same-level child containers, set the gap between adjacent container borders to exactly 10px.
   - For a direct content group (child containers, terminal leaf rectangles, and allowed responsibility/note text), set the distance from the group's bottom border to the parent container's bottom border to exactly 10px.
   - For leaf-only groups, keep top padding near the normal content start: 20px for untitled containers, or 8px below a title band for titled containers. Do not vertically center sparse leaf lists by adding large top and bottom whitespace.
   - Keep enough horizontal gap between sibling containers that wrapped labels and borders do not feel crowded.
   - Avoid over-loose spacing between same-level containers; use a consistent moderate rhythm instead of expanding gaps just to fill the parent.

5. Align peer containers:
   - Calculate each peer's content width first.
   - Normalize peer container width to the maximum width for that level when widths are close or visual alignment is needed.
   - Normalize peer container height to the maximum height for that level when heights are close or visual alignment is needed.
   - For visually paired containers such as `frontend component layer` and `backend framework layer`, equalize heights when their natural heights are close; for peer containers with similar widths, equalize widths.
   - Recompute child-group centered coordinates after width normalization.
   - After width or height normalization, recenter child groups and preserve parent padding.

6. Preserve padding:
   - Content area left/right padding: at least 20px.
   - Space below title: at least 8px.
   - Direct content group bottom gap: exactly 10px.
   - Leaf-only group bottom gap: exactly 10px; top padding should stay compact instead of mirrored/centered.

7. Represent lists as grouped or contained nodes, not loose naked nodes. Bare text is allowed only for responsibility notes, light annotations, connector labels, or numbering explanations.

Use this sizing rhythm unless the source clearly requires another layout:

- Measure text before sizing nodes: Chinese characters count wider than ASCII; prefer one line until the node would become unwieldy.
- Leaf nodes: start around 36px high, then add 18-22px per wrapped line plus vertical padding.
- Horizontal sibling gaps: usually 12-20px.
- Vertical same-level child-container gaps: exactly 10px.
- Parent width: sibling group width plus at least 40px content padding, and usually plus extra breathing room when titles or wrapped labels need it.
- Parent height: title band plus content group height plus at least 8px below title and 10px bottom gap for direct content groups, including leaf-only groups.
- After normalizing peer widths/heights, recalculate child-group centering; never leave children stuck to the old left edge.

## Category Guidance

Use `architecture` when the block contains nested boxes, platform layers, modules, components, infrastructure, system boundaries, or many box-drawing borders.

Use `flowchart` when the block emphasizes order, branching, state transitions, start/end points, decision labels, or a directional pipeline.

Use `sequence` when the block emphasizes actors/components exchanging messages over time, arrows between participants, lifelines, or chronological request/response steps.

If multiple categories match, prefer architecture for real nested containers, then sequence for lifelines/messages, then flowchart for state/step transitions.

## XML Generation Guidance

- Prefer simple draw.io primitives: rounded rectangles, swimlanes or parent containers, text labels, orthogonal connectors, and grouped leaf nodes.
- Convert ASCII/Unicode boxes, borders, lifelines, and arrows into real draw.io containers, shapes, and connectors. Do not preserve box-drawing characters as the visual structure.
- For architecture diagrams, represent parent/child relationships with nested containers or clearly grouped regions, not only peer cards.
- For architecture diagrams, prefer real nested `mxCell parent` relationships over top-level absolute positioning. The visible parent-child hierarchy, XML parent ids, and source container tree must agree.
- Use stable, descriptive cell ids such as `container-platform`, `leaf-upload-widget`, or `edge-client-service`; keep ids unique within a page.
- Include root sentinels:
  ```xml
  <mxCell id="0"/>
  <mxCell id="1" parent="0"/>
  ```
- For containers, use a real title area: prefer `swimlane`/container styles or set `verticalAlign=top;spacingTop=8;` and place children below the title band. Do not let parent labels render in the visual center behind child nodes.
- Keep style strings explicit: `rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=14;`.
- If a cell value contains inline HTML such as `<b>`, `<span>`, or `<br>`, the cell style must include `html=1`. If the label only needs plain text, remove the tags instead of escaping them into visible text.
- Use color to separate layers and roles, but avoid relying on color alone to encode structure.
- For sequence diagrams, align participants horizontally, messages vertically, and keep arrows from overlapping labels.
- For flowcharts, route top-to-bottom or left-to-right consistently and keep decision branches readable.
- Before export, run `scripts/lint_drawio_xml.py` on the XML. Fix all errors, especially missing `rounded=1;arcSize=1`, missing `html=1` on valued cells, visible HTML tags in labels, font sizes below 13px, missing Chinese font family, box-drawing text in values, visual parent/XML parent mismatches, child overflow, title-area invasion, loose vertical child-container gaps, direct content group bottom gaps other than 10px, excessive leaf-only top padding, and multi-page XML.

## Subagent Prompt Templates

Generation prompt:

````text
Use $diagram-to-image to generate draw.io XML for one Markdown text diagram.

Category: CATEGORY
Output XML path: OUTPUT_XML

Source block:
```text
BLOCK_CONTENT
```

Follow the skill constraints. For architecture diagrams, first analyze the container tree and layout, then write exactly one single-page draw.io XML file. Do not create PNGs.

If Category is architecture, read `references/architecture-layout-algorithm.md` first and include the required container tree, layout summary, and self-check before the XML.
````

XML review prompt:

```text
Use $diagram-to-image to review one draw.io XML file before PNG export.

Category: CATEGORY
Source block path or text: SOURCE
XML path: XML_PATH

Apply references/xml-review-checklist.md. Report PASS or FAIL with blocking fixes. Do not export PNGs.
```

## Completion Checklist

Before finishing, verify:

- The workflow task list was created before Step 1 and updated through the full run.
- Every Required Workflow step has terminal status `DONE`, `SKIPPED: reason`, or `UNRESOLVED: reason`.
- Every skipped item includes a concrete reason.
- Steps 4-7 are tracked separately for each user-selected source block id.
- Every user-selected diagram has one PNG output, or a clearly documented unresolved status after retries.
- The final summary notes extracted diagrams that were not selected and therefore intentionally skipped.
- Every PNG came from a separate drawio MCP create/browser/export cycle with only one diagram XML.
- Every drawio MCP create/browser/export cycle ran serially, and no diagram was exported before explicit user approval in the browser or `AUTO-PASSED: manual_review_bypass=true`.
- Unless `manual_review_bypass=true`, no diagram was exported before explicit user approval in the browser.
- When `manual_review_bypass=true`, every affected diagram records `AUTO-PASSED: manual_review_bypass=true` as the human approval outcome.
- The final summary records each diagram's human approval outcome as passed, auto-passed, or rejected/regenerated attempts.
- Every XML passed XML review or was fixed after review.
- Every XML passed `scripts/lint_drawio_xml.py` with no errors.
- Every architecture XML's source container tree, visible containment, and `mxCell parent` hierarchy agree. Do not rely on comments or self-check prose to claim this.
- Architecture diagrams have documented container-tree analysis, layout summary, and self-check from `references/architecture-layout-algorithm.md`.
- The final summary maps Markdown block ids to PNG paths.
