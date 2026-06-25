# Architecture Layout Algorithm

Use this reference when generating or repairing architecture diagrams. The goal is faithful structure, correct containment, readable text, and a compact canvas. Do not write XML until the container tree and layout numbers are known.

## Required Output Before XML

For every architecture diagram, write a short analysis block before the XML:

```text
Container tree:
- root: ...
  - parent: ...
    - sibling group: [...]
    - leaf items: [...]

Layout:
- traversal: inner-to-outer sizing, outer-to-inner placement
- normalized peer groups: ...
- XML parent plan: every non-root child uses its semantic container id as `parent`
- canvas: width x height
- self-check: XML parents match the source container tree, no overflow, balanced padding, no sibling overlap
```

## Stage A: Build The Container Tree

- Treat a box enclosed by another box as a child container.
- Treat direct children under the same parent as one sibling group.
- Treat list-like contents inside a box as leaf items. Each leaf item must become its own rounded rectangle, not a naked text stack.
- Treat leaf items as terminal containers for layout: they are the smallest content boxes, not free-floating text. Leaf-only groups must be sized and positioned with the same compact direct-content rules as child-container groups.
- Use a title band for titled containers. Prefer `startSize=28` for swimlanes. If a container has no title band, reserve a top padding of at least 20px.
- Assign stable ids while building the tree. Every non-root child container and leaf item must record the id of its semantic parent container.
- Keep semantic names from the source. Do not add domain content that is not present or clearly implied.

## Stage B: Size From Leaves To Root

### Text Measurement

Estimate label width before choosing geometry:

```text
textWidth = Chinese chars * 18 + ASCII letters/digits * 10 + punctuation/symbols * 8 + 24
leafWidth = ceil to next 10px
leafHeight = 36px minimum
```

Long labels:

- Prefer one line while `textWidth <= 350`.
- If a label would be too wide, wrap at 350-520px and increase height by roughly `lineCount * 20 + 12`.
- After wrapping, recalculate parent height and bottom padding.

### Sibling Group Size

Calculate the group before positioning it inside the parent.

Use `gapX=12-20`. For vertically stacked same-level child containers, use `containerGapY=10` exactly. For vertically stacked leaf items, prefer `gapY=10` unless text wrapping needs more room. Keep gaps consistent inside one group.

For horizontal siblings:

```text
groupWidth = sum(child.width) + gapX * (n - 1)
groupHeight = max(child.height)
```

For vertical siblings:

```text
groupWidth = max(child.width)
groupHeight = sum(child.height) + gapY * (n - 1)
```

For grid siblings:

```text
itemWidth = max(child.width)
itemHeight = max(child.height)
groupWidth = itemWidth * columns + gapX * (columns - 1)
groupHeight = itemHeight * rows + gapY * (rows - 1)
```

### Peer Normalization

For same-level containers:

1. Calculate each container's natural content width and height.
2. If peer widths are close or the source implies aligned columns, set all peer widths to the maximum peer width.
3. If peer heights are close or the source implies paired panels, set all peer heights to the maximum peer height.
4. Recompute every child-group `groupStartX` and `groupStartY` after normalization.

Use this for paired containers such as "frontend component layer" and "backend framework layer" when their natural heights differ only modestly.

### Parent Size

Reserve padding:

```text
contentPadX = 20
titleGap = 8
bottomPad = 10
extraBreathingX = 40
```

When a parent contains direct content (child containers, terminal leaf rectangles, and allowed responsibility/note text), the direct content group must end exactly 10px above the parent bottom border. Do not leave extra blank area below the group to make the parent taller.

Common formula:

```text
containerWidth = groupWidth + 2 * contentPadX + extraBreathingX
```

For titled containers:

```text
contentStartY = startSize + titleGap
containerHeight = contentStartY + groupHeight + bottomPad
```

For untitled containers:

```text
contentStartY = 20
containerHeight = contentStartY + groupHeight + bottomPad
```

For leaf-only groups, keep `contentStartY` compact. Do not vertically center sparse leaf lists by mirroring large top and bottom padding inside an oversized parent.

If a responsibility note is present, include its measured height in the group height. Responsibility notes may be text nodes; list items may not.

## Stage C: Place From Root To Leaves

### Root

Place the outermost root at `(20, 20)` and set the canvas to content bounds plus 20px:

```text
pageWidth = maxRight + 20
pageHeight = maxBottom + 20
```

### Parent Content Area

For each parent:

```text
contentX = 20
contentWidth = parentWidth - 40
contentY = startSize + 8  # titled
contentY = 20             # untitled
```

Use nested `mxCell parent` ids for architecture diagrams. Child coordinates are relative to their semantic parent container. Keep only true root-level containers under `parent="1"`; do not place nested children under `parent="1"` with absolute coordinates.

### Center Sibling Groups

Horizontal group:

```text
groupStartX = contentX + (contentWidth - groupWidth) / 2
childX(i) = groupStartX + sum(previous widths) + gapX * i
childY = contentY
```

Vertical group:

```text
childX = contentX + (contentWidth - childWidth) / 2
childY(i) = contentY + sum(previous heights) + gapY * i
```

Grid group:

```text
groupStartX = contentX + (contentWidth - groupWidth) / 2
childX = groupStartX + col * (itemWidth + gapX)
childY = contentY + row * (itemHeight + gapY)
```

## Required Self-Check

For every parent container, verify:

- `leftPad >= 20`
- `rightPad >= 20`
- `abs(leftPad - rightPad) <= 5` when practical
- `topPad >= 8` below a title band, or `topPad >= 20` for untitled containers
- `topPad` is not loose: use about 8px below a title band, or about 20px for untitled containers
- `bottomPad == 10` for every direct content group, including leaf-only groups
- every child right edge is `<= parentWidth`
- every child bottom edge is `<= parentHeight`
- every child has the same XML parent id as its source container-tree parent
- vertical same-level child-container gap is exactly 10px
- other sibling gaps are at least 10px
- no sibling rectangles overlap

For every architecture XML, include compact comments for important parents:

```xml
<!-- layout-check parent=FileProvider left=20 right=20 top=8 bottom=10 gapY=10 centered no-overlap no-overflow -->
```

## Common Failures To Fix

| Failure | Fix |
|---|---|
| XML written before a container tree exists | Stop and produce the tree, then regenerate layout |
| Children invade the title band | Use `contentY = startSize + 8` |
| Children are inside the visual parent but have `parent="1"` unnecessarily | Use the real parent container id and relative coordinates |
| Layout comments say children are nested but XML parents are flat | Regenerate the XML parent tree from the container tree; comments are not validation evidence |
| Peer containers align visually but children stay left-biased | Recompute group centering after width/height normalization |
| List items rendered as one text block | Split into individual rounded leaf rectangles |
| Parent is much wider than content | Recalculate from sibling group width, then add only required padding |
| Vertically stacked child containers have loose or uneven gaps | Set every same-level child-container vertical gap to exactly 10px |
| Parent has blank space below the direct content group | Recalculate parent height so the content group bottom is exactly 10px above the parent border |
| Leaf-only group is vertically centered in a tall parent | Treat leaves as terminal containers; shrink the parent or move the leaf group to compact top padding with a 10px bottom gap |
| Canvas has large right/bottom blank area | Set page dimensions from max content bounds plus 20px |
