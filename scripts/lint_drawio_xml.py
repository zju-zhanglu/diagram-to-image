#!/usr/bin/env python3
"""Lint draw.io XML for diagram-to-image constraints."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


ALLOWED_TEXT_PREFIXES = ("职责", "说明", "注", "注释", "事件", "条件", "序号")
RECT_EXCLUDE = ("text;", "shape=line", "line;", "edgeLabel", "group")
BOX_DRAWING_RE = re.compile(r"[┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣╦╩╬╭╮╰╯]{3,}")
ASCII_BORDER_RE = re.compile(r"(\+-{2,}\+|^\|[^|]{0,120}\|$|^\+[-+]{3,}$)")
HTML_TAG_RE = re.compile(r"</?(?:b|strong|i|em|span|br|font|div|p)\b[^>]*>", re.IGNORECASE)
HTML_ENTITY_TAG_RE = re.compile(r"&lt;/?(?:b|strong|i|em|span|br|font|div|p)\b[^&]*&gt;", re.IGNORECASE)
CONTAINER_GAP = 10.0
LAYOUT_TOLERANCE = 0.5
MIN_VISUAL_PARENT_OVERLAP = 0.25
MAX_TOP_PADDING_SLACK = 10.0

Box = tuple[float, float, float, float]


def parse_style(style: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in style.split(";"):
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            result[key] = value
        else:
            result[part] = "1"
    return result


def num(value: str | None, default: float = 0) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def overlaps(a: Box, b: Box) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def contains(outer: Box, inner: Box) -> bool:
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return ix >= ox and iy >= oy and ix + iw <= ox + ow and iy + ih <= oy + oh


def area(box: Box) -> float:
    return max(box[2], 0) * max(box[3], 0)


def intersection_area(a: Box, b: Box) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    width = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    height = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    return width * height


def close_to(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= LAYOUT_TOLERANCE


def is_container_cell(cell: ET.Element, style_text: str, child_parent_ids: set[str]) -> bool:
    cid = cell.attrib.get("id", "")
    return "swimlane" in style_text or cid in child_parent_ids


def to_parent_space(child_abs: Box, parent_abs: Box) -> Box:
    cx, cy, cw, ch = child_abs
    px, py, _, _ = parent_abs
    return (cx - px, cy - py, cw, ch)


def diagrams(root: ET.Element) -> list[tuple[str, ET.Element]]:
    if local_name(root.tag) == "mxGraphModel":
        return [("Page-1", root)]

    found: list[tuple[str, ET.Element]] = []
    for diagram in root.iter():
        if local_name(diagram.tag) != "diagram":
            continue
        name = diagram.attrib.get("name", diagram.attrib.get("id", "diagram"))
        model = next((child for child in diagram if local_name(child.tag) == "mxGraphModel"), None)
        if model is not None:
            found.append((name, model))
    return found


def lint_model(name: str, model: ET.Element) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    cells = [el for el in model.iter() if local_name(el.tag) == "mxCell"]
    by_id = {cell.attrib.get("id", ""): cell for cell in cells}
    vertices = [cell for cell in cells if cell.attrib.get("vertex") == "1"]

    raw_geometries: dict[str, Box] = {}
    for cell in vertices:
        geom = next((child for child in cell if local_name(child.tag) == "mxGeometry"), None)
        if geom is None:
            continue
        x, y = num(geom.attrib.get("x")), num(geom.attrib.get("y"))
        w, h = num(geom.attrib.get("width")), num(geom.attrib.get("height"))
        raw_geometries[cell.attrib.get("id", "")] = (x, y, w, h)

    absolute_cache: dict[str, Box] = {}

    def absolute_geometry(cid: str) -> Box | None:
        if cid in absolute_cache:
            return absolute_cache[cid]
        if cid not in raw_geometries:
            return None
        x, y, w, h = raw_geometries[cid]
        parent_id = by_id.get(cid, ET.Element("mxCell")).attrib.get("parent")
        if parent_id and parent_id not in ("0", "1") and parent_id in raw_geometries:
            parent_abs = absolute_geometry(parent_id)
            if parent_abs is not None:
                px, py, _, _ = parent_abs
                x += px
                y += py
        absolute_cache[cid] = (x, y, w, h)
        return absolute_cache[cid]

    child_parent_ids = {cell.attrib.get("parent", "") for cell in vertices if cell.attrib.get("parent") not in (None, "0", "1")}
    container_ids = {
        cell.attrib.get("id", "")
        for cell in vertices
        if is_container_cell(cell, cell.attrib.get("style", ""), child_parent_ids) and cell.attrib.get("id", "") in raw_geometries
    }
    absolute_geometries = {
        cid: geom
        for cid in raw_geometries
        if (geom := absolute_geometry(cid)) is not None
    }

    def inferred_visual_parent(cid: str) -> str | None:
        child_box = absolute_geometries.get(cid)
        if child_box is None:
            return None

        containing: list[tuple[float, str]] = []
        overlapping: list[tuple[float, float, str]] = []
        child_area = area(child_box)

        for candidate_id in container_ids:
            if candidate_id == cid:
                continue
            candidate_box = absolute_geometries.get(candidate_id)
            if candidate_box is None:
                continue
            if contains(child_box, candidate_box):
                continue
            if contains(candidate_box, child_box):
                containing.append((area(candidate_box), candidate_id))
                continue
            if child_area > 0:
                overlap_ratio = intersection_area(candidate_box, child_box) / child_area
                if overlap_ratio >= MIN_VISUAL_PARENT_OVERLAP:
                    overlapping.append((overlap_ratio, -area(candidate_box), candidate_id))

        if containing:
            return min(containing)[1]
        if overlapping:
            return max(overlapping)[2]
        return None

    inferred_parent_by_id = {cid: inferred_visual_parent(cid) for cid in raw_geometries}

    max_right = 0.0
    max_bottom = 0.0
    for cid in raw_geometries:
        abs_geom = absolute_geometry(cid)
        if abs_geom is None:
            continue
        x, y, w, h = abs_geom
        max_right = max(max_right, x + w)
        max_bottom = max(max_bottom, y + h)

    for cell in vertices:
        cid = cell.attrib.get("id", "")
        style_text = cell.attrib.get("style", "")
        style = parse_style(style_text)
        raw_value = cell.attrib.get("value", "")
        value = re.sub(r"<[^>]+>", "", raw_value).strip()
        is_text = "text" in style or style_text.startswith("text;")
        is_line = "shape=line" in style_text or "line" in style
        is_rect_like = not is_text and not is_line and not any(token in style_text for token in RECT_EXCLUDE)

        if raw_value and style.get("html") != "1":
            issues.append({"page": name, "id": cid, "severity": "error", "message": "valued vertex missing html=1"})
        if (HTML_TAG_RE.search(raw_value) or HTML_ENTITY_TAG_RE.search(raw_value)) and style.get("html") != "1":
            issues.append({"page": name, "id": cid, "severity": "error", "message": "HTML-like tag markup will render as visible text without html=1"})

        if BOX_DRAWING_RE.search(value):
            issues.append({"page": name, "id": cid, "severity": "error", "message": "box-drawing text appears in rendered value"})
        if ASCII_BORDER_RE.search(value):
            issues.append({"page": name, "id": cid, "severity": "error", "message": "ASCII border art appears in rendered value"})

        if is_rect_like:
            if style.get("rounded") != "1":
                issues.append({"page": name, "id": cid, "severity": "error", "message": "rectangular vertex missing rounded=1"})
            if style.get("arcSize") != "1":
                issues.append({"page": name, "id": cid, "severity": "error", "message": "rectangular vertex missing arcSize=1"})

        font_size = num(style.get("fontSize"), 13)
        if value and font_size < 13:
            issues.append({"page": name, "id": cid, "severity": "error", "message": f"fontSize {font_size:g} < 13"})

        font_family = style.get("fontFamily", "")
        if value and re.search(r"[\u4e00-\u9fff]", value) and font_family not in ("PingFang SC", "Microsoft YaHei"):
            issues.append({"page": name, "id": cid, "severity": "error", "message": "Chinese label missing PingFang SC or Microsoft YaHei"})

        if is_text and value and not value.startswith(ALLOWED_TEXT_PREFIXES):
            issues.append({"page": name, "id": cid, "severity": "warning", "message": "bare text node; ensure it is not a list item"})

        parent_id = cell.attrib.get("parent")
        inferred_parent_id = inferred_parent_by_id.get(cid)
        if inferred_parent_id and parent_id != inferred_parent_id:
            issues.append(
                {
                    "page": name,
                    "id": cid,
                    "severity": "error",
                    "xml_parent": parent_id or "",
                    "inferred_visual_parent": inferred_parent_id,
                    "message": f"visual parent is {inferred_parent_id} but XML parent is {parent_id or '-'}",
                }
            )
        if parent_id and parent_id not in ("0", "1") and cid in absolute_geometries and parent_id in absolute_geometries:
            child_box = to_parent_space(absolute_geometries[cid], absolute_geometries[parent_id])
            _, _, pw, ph = raw_geometries[parent_id]
            x, y, w, h = child_box
            if x < 0 or y < 0 or x + w > pw or y + h > ph:
                issues.append({"page": name, "id": cid, "severity": "error", "message": f"child exceeds parent {parent_id}"})

    children_by_parent: dict[str, list[str]] = {}
    for cell in vertices:
        cid = cell.attrib.get("id", "")
        if cid not in raw_geometries:
            continue
        inferred_parent_id = inferred_parent_by_id.get(cid)
        parent_id = cell.attrib.get("parent")
        effective_parent_id = inferred_parent_id or (parent_id if parent_id not in (None, "0", "1") else None)
        if effective_parent_id and effective_parent_id in raw_geometries:
            children_by_parent.setdefault(effective_parent_id, []).append(cid)

    for parent_id, child_ids in children_by_parent.items():
        _, _, pw, ph = raw_geometries[parent_id]
        child_entries = [
            (child_id, to_parent_space(absolute_geometries[child_id], absolute_geometries[parent_id]))
            for child_id in child_ids
            if child_id in absolute_geometries and parent_id in absolute_geometries
        ]
        child_boxes = [box for _, box in child_entries]
        if not child_boxes:
            continue

        parent_style = parse_style(by_id[parent_id].attrib.get("style", ""))
        start_size = num(parent_style.get("startSize"), 0)
        title_clearance = start_size + 8 if start_size else 0
        expected_top_padding = 8.0 if start_size else 20.0

        for child_id, (x, y, w, h) in child_entries:
            if x < 0 or y < title_clearance or x + w > pw or y + h > ph:
                issues.append(
                    {
                        "page": name,
                        "id": child_id,
                        "severity": "error",
                        "parent": parent_id,
                        "message": f"child exceeds visual parent {parent_id} content bounds",
                    }
                )

        for index, (left_id, left_box) in enumerate(child_entries):
            for right_id, right_box in child_entries[index + 1 :]:
                if overlaps(left_box, right_box):
                    issues.append(
                        {
                            "page": name,
                            "id": parent_id,
                            "severity": "error",
                            "message": f"sibling overlap between {left_id} and {right_id}",
                        }
                    )

        min_x = min(x for x, _, _, _ in child_boxes)
        min_y = min(y for _, y, _, _ in child_boxes)
        max_r = max(x + w for x, _, w, _ in child_boxes)
        max_b = max(y + h for _, y, _, h in child_boxes)
        pads = {
            "left": min_x,
            "right": pw - max_r,
            "top": min_y - start_size if start_size else min_y,
            "bottom": ph - max_b,
        }
        for side, pad in pads.items():
            if side in ("left", "right"):
                minimum = 20
            elif side == "bottom":
                minimum = 10
            else:
                minimum = expected_top_padding
            if pad < minimum:
                issues.append(
                    {
                        "page": name,
                        "id": parent_id,
                        "severity": "warning",
                        "message": f"child group {side} padding {pad:g}px < {minimum}px",
                    }
                )
        if pads["top"] > expected_top_padding + MAX_TOP_PADDING_SLACK:
            issues.append(
                {
                    "page": name,
                    "id": parent_id,
                    "severity": "error",
                    "message": f"direct content group top padding {pads['top']:g}px is too loose; expected about {expected_top_padding:g}px",
                }
            )
        if pads["left"] >= 20 and pads["right"] >= 20 and abs(pads["left"] - pads["right"]) > 5:
            issues.append(
                {
                    "page": name,
                    "id": parent_id,
                    "severity": "warning",
                    "message": f"child group not centered: left={pads['left']:g}px right={pads['right']:g}px",
                }
            )

        direct_content_bottom_gap = ph - max_b
        if not close_to(direct_content_bottom_gap, CONTAINER_GAP):
            issues.append(
                {
                    "page": name,
                    "id": parent_id,
                    "severity": "error",
                    "message": f"direct content group bottom gap {direct_content_bottom_gap:g}px != {CONTAINER_GAP:g}px",
                }
            )

        container_entries = [
            (cid, box, child_cell)
            for cid, box in (
                (
                    child_id,
                    to_parent_space(absolute_geometries[child_id], absolute_geometries[parent_id]),
                )
                for child_id in child_ids
                if child_id in absolute_geometries and parent_id in absolute_geometries and child_id in by_id
            )
            for child_cell in [by_id[cid]]
            if is_container_cell(child_cell, child_cell.attrib.get("style", ""), child_parent_ids)
        ]
        if not container_entries:
            continue

        sorted_entries = sorted(container_entries, key=lambda entry: (entry[1][1], entry[1][0]))
        rows: list[dict[str, float]] = []
        for _, (x, y, w, h), _ in sorted_entries:
            bottom = y + h
            if rows and y < rows[-1]["bottom"] - LAYOUT_TOLERANCE:
                rows[-1]["top"] = min(rows[-1]["top"], y)
                rows[-1]["bottom"] = max(rows[-1]["bottom"], bottom)
                rows[-1]["left"] = min(rows[-1]["left"], x)
                rows[-1]["right"] = max(rows[-1]["right"], x + w)
            else:
                rows.append({"top": y, "bottom": bottom, "left": x, "right": x + w})

        for index, upper_row in enumerate(rows[:-1]):
            lower_row = rows[index + 1]
            gap = lower_row["top"] - upper_row["bottom"]
            if not close_to(gap, CONTAINER_GAP):
                issues.append(
                    {
                        "page": name,
                        "id": parent_id,
                        "severity": "error",
                        "message": f"vertical child-container row gap {gap:g}px != {CONTAINER_GAP:g}px",
                    }
                )

    page_width = num(model.attrib.get("pageWidth"), max_right + 20)
    page_height = num(model.attrib.get("pageHeight"), max_bottom + 20)
    if page_width < max_right:
        issues.append({"page": name, "severity": "error", "message": f"pageWidth {page_width:g}px clips content ending at {max_right:g}px"})
    if page_height < max_bottom:
        issues.append({"page": name, "severity": "error", "message": f"pageHeight {page_height:g}px clips content ending at {max_bottom:g}px"})
    if page_width - max_right > 40:
        issues.append({"page": name, "severity": "warning", "message": f"right blank {page_width - max_right:g}px > 40px"})
    if page_height - max_bottom > 40:
        issues.append({"page": name, "severity": "warning", "message": f"bottom blank {page_height - max_bottom:g}px > 40px"})

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        root = ET.parse(args.xml).getroot()
    except ET.ParseError as exc:
        print(json.dumps({"ok": False, "issues": [{"severity": "error", "message": str(exc)}]}, ensure_ascii=False, indent=2))
        return 2

    issues: list[dict[str, object]] = []
    pages = diagrams(root)
    if not pages:
        issues.append({"severity": "error", "message": "no mxGraphModel found"})
    if len(pages) != 1:
        issues.append({"severity": "error", "message": f"expected exactly one diagram page, found {len(pages)}"})
    for page_name, model in pages:
        issues.extend(lint_model(page_name, model))

    ok = not any(issue.get("severity") == "error" for issue in issues)
    payload = {"ok": ok, "pages": len(pages), "issues": issues}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"ok={ok} pages={len(pages)} issues={len(issues)}")
        for issue in issues:
            prefix = issue.get("severity", "info").upper()
            page = issue.get("page", "-")
            cid = issue.get("id", "-")
            print(f"[{prefix}] page={page} id={cid} {issue['message']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
