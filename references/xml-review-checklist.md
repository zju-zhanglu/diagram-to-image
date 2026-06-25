# XML Review Checklist

Use this checklist before exporting any draw.io XML to PNG.

## Blocking Issues

- The XML contains more than one diagram page or more than one independent diagram.
- The output is a raw rendering of the original ASCII/Unicode block instead of a graphical reconstruction.
- Box-drawing characters such as `┌`, `─`, `│`, `└`, or ASCII border art provide the main structure of the final image.
- Source ASCII/Unicode borders are preserved as labels instead of converted into draw.io geometry.
- Any rectangular shape lacks `rounded=1` or `arcSize=1`.
- Any valued vertex is missing `html=1` in its style.
- Inline HTML tags such as `<b>`, `<span>`, or `<br>` are escaped or rendered as visible text instead of being interpreted by draw.io.
- Any default text size is below 13px.
- Chinese-capable labels do not specify `fontFamily=PingFang SC` or a justified fallback.
- Child containers or leaf nodes visually cross parent borders or title areas.
- A child is visually inside or attached to a container but its XML `parent` is `1` or a different container.
- The source container tree, visible containment, and XML `mxCell parent` hierarchy disagree.
- Layout comments, `Container tree` prose, or self-check notes claim containment that the XML parent ids or rendered geometry do not satisfy.
- Container titles render behind or overlap child content instead of staying in a top title area.
- Same-parent containers overlap instead of forming a centered sibling group.
- Vertically stacked same-level child containers do not use an exact 10px gap between adjacent container borders.
- A direct child-container group does not end exactly 10px above the parent container's bottom border.
- Same-parent containers are so close that their labels, borders, or wrapped child text feel visually crowded.
- Same-parent containers are unnecessarily far apart while leaf nodes inside those containers are cramped.
- Peer containers with similar heights are left visually uneven instead of being normalized to the maximum height.
- Peer containers with similar widths are left visually uneven instead of being normalized to the maximum width.
- Wrapped child labels touch or exceed their parent bounds instead of leaving clear bottom padding.
- Wrapped leaf nodes do not increase height according to their rendered line count.
- Connectors pass through important labels or shapes.
- The canvas has clipped content, large empty space, or off-canvas elements.
- Source labels, hierarchy, or relationships are missing without explanation.
- The XML uses one large text cell, a `<pre>` block, or line-by-line text cells as a substitute for graphical draw.io shapes.
- A nested/container diagram has been flattened into unrelated peer cards, losing parent-child hierarchy or sibling groups.

## Architecture Review

- Confirm the generator produced a container tree before XML.
- Confirm the generator applied `references/architecture-layout-algorithm.md` and included a layout summary/self-check before XML.
- Check parent-child relationships in both XML ids/parents and visible geometry.
- Verify every non-root child container and leaf item uses the semantic source parent as its XML `parent`, with coordinates relative to that parent.
- Check that each child position was calculated from its parent and same-level siblings, then adjusted recursively for containment and centering.
- Check that sibling rectangles under the same parent do not overlap; vertical child-container groups must use exactly 10px gaps unless the source explicitly depicts touching boundaries.
- Verify per-parent padding: 20px left/right, 8px below titles, and 10px below direct child-container groups.
- Check that child groups are centered inside the parent content area; left/right padding should be balanced within about 5px when practical.
- Check that peer containers align where the source implies a shared level.
- Check that similar peer widths/heights are normalized to the level maximum and child groups are recentered after normalization.
- Ensure list-like content is represented as contained items, not loose naked nodes.

## Flowchart Review

- Confirm the main reading direction is consistent.
- Check that branches have readable labels when the source provides them.
- Verify start/end/process/decision nodes have distinct visual treatment.
- Ensure orthogonal connectors do not share ambiguous paths.

## Sequence Review

- Confirm participants are ordered consistently with the source.
- Check messages are chronological and vertically spaced.
- Keep request/response arrows readable and label-aligned.
- Avoid crossing lifelines or overlapping message labels.

## Pass Criteria

Return `PASS` only when the XML can be exported as a faithful, readable, compact single PNG and is expected to pass `scripts/lint_drawio_xml.py` with no errors. Return `FAIL` with concrete fixes for any blocking issue.
