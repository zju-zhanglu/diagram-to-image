# Visual Review Checklist

Use this checklist after exporting one PNG from one Markdown text diagram. Compare the PNG against the original ASCII/Unicode block, not against the generated XML alone.

Batch rule: review and repair one diagram at a time. Do not wait until the whole batch is exported before visual review.

## Review Focus

1. Rectangles: every rectangular container, component, state, participant, and note-like box must look lightly rounded, consistent with `rounded=1;arcSize=1`; large pill corners are not acceptable unless the shape is intentionally not a rectangle.
2. Text: every source label must appear, be readable, and avoid truncation, overlap, mojibake, tiny font rendering, or visible escaped HTML tags such as `<b>`, `<span>`, or `<br>`.
3. Architecture hierarchy: parent containers, child containers, sibling container groups, and leaf items must match the source. Children must be fully inside parents and must not invade title bands.
4. Architecture centering and padding: child groups must be centered inside parent content areas. Left/right padding should be balanced within about 5px when possible; bottom padding must remain visible.
5. Architecture sibling groups: containers or leaf items with the same parent must not overlap. Vertically stacked same-level child containers must use exact 10px gaps, direct child-container groups must end exactly 10px above the parent bottom border, and horizontal groups should not be stretched apart just to fill space.
6. Flowcharts and state machines: node order, branch direction, transition labels, error/cancel/retry paths, and start/end semantics must match the source.
7. Sequence diagrams: participant order, lifeline alignment, message order, request/response direction, and message labels must match the source.
8. List representation: list items inside containers must be individual rounded boxes or grouped items, not a naked text stack.
9. Canvas: the image must be tight around content, with no clipping and no right/bottom blank area over roughly 40px.
10. Connectors: lines must not cross critical text or create ambiguous targets. Orthogonal routing and waypoints should be used where needed.
11. Overall readability: the diagram should be balanced and professional enough to be useful in documentation.

## PASS Criteria

Return `PASS` only when the score is at least 7/10 and there is no structural error. A structural error includes child overflow, wrong hierarchy, missing source labels, wrong flow direction, wrong sequence order, unreadable text, or visually missing rounded rectangle styling.

## Output Format

Return:

```json
{
  "overall": "PASS|FAIL",
  "score": 7,
  "checks": [
    {"name": "text", "result": "PASS|FAIL", "details": "..."},
    {"name": "structure", "result": "PASS|FAIL", "details": "..."},
    {"name": "routing", "result": "PASS|FAIL", "details": "..."},
    {"name": "canvas", "result": "PASS|FAIL", "details": "..."}
  ],
  "failures": [
    {"description": "specific issue", "fix": "specific XML/layout change to try next"}
  ]
}
```
