"""Extract likely ASCII/Unicode diagrams from Markdown and classify them."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


BOX_CHARS = set("+-|/\\_=~*#.:;[]{}()<>")
UNICODE_BOX_CHARS = set("┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣╦╩╬╭╮╰╯")
ARROW_RE = re.compile(r"(--?>|==?>|<--?|<==?|->>|<<-|=>|⇄|→|←|↔|⇒|⇐|↦)")
SEQUENCE_RE = re.compile(r"(\w[\w .:/-]{0,40})\s*(-+>|=+>|->>|-->>|<--|<==|←|→|⇒)")
FLOW_WORD_RE = re.compile(r"\b(start|end|if|else|yes|no|true|false|decision|process|done|fail|success)\b", re.I)
ARCH_WORD_RE = re.compile(
    r"\b(layer|module|service|component|adapter|domain|infra|client|server|database|db|cache|redis|mysql|api|ui|web|front[- ]?end|back[- ]?end)\b",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", type=Path, help="Markdown file to scan")
    parser.add_argument("--out", type=Path, help="Write JSON to this path")
    parser.add_argument("--include-indented", action="store_true", help="Also scan 4-space indented code blocks")
    return parser.parse_args()


def heading_for_line(lines: list[str], line_index: int) -> str:
    for index in range(line_index - 1, -1, -1):
        stripped = lines[index].strip()
        if stripped.startswith("#"):
            return stripped
    return ""


def extract_fenced_blocks(lines: list[str]) -> list[dict]:
    blocks: list[dict] = []
    fence_re = re.compile(r"^(\s*)(`{3,}|~{3,})([^`]*)$")
    index = 0
    while index < len(lines):
        match = fence_re.match(lines[index].rstrip("\n"))
        if not match:
            index += 1
            continue
        fence = match.group(2)
        lang = match.group(3).strip()
        start = index
        index += 1
        content: list[str] = []
        while index < len(lines):
            if lines[index].strip().startswith(fence):
                break
            content.append(lines[index].rstrip("\n"))
            index += 1
        end = index if index < len(lines) else len(lines) - 1
        blocks.append(
            {
                "start_line": start + 1,
                "end_line": end + 1,
                "fence": lang,
                "heading": heading_for_line(lines, start),
                "content": "\n".join(content).strip("\n"),
            }
        )
        index += 1
    return blocks


def extract_indented_blocks(lines: list[str]) -> list[dict]:
    blocks: list[dict] = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith(("    ", "\t")):
            index += 1
            continue
        start = index
        content: list[str] = []
        while index < len(lines) and (lines[index].startswith(("    ", "\t")) or not lines[index].strip()):
            line = lines[index]
            content.append(line[4:] if line.startswith("    ") else line.lstrip("\t"))
            index += 1
        blocks.append(
            {
                "start_line": start + 1,
                "end_line": index,
                "fence": "indented",
                "heading": heading_for_line(lines, start),
                "content": "\n".join(content).strip("\n"),
            }
        )
    return blocks


def diagram_score(text: str) -> tuple[int, list[str]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return 0, ["too few non-empty lines"]

    joined = "\n".join(lines)
    char_count = sum(1 for char in joined if char in BOX_CHARS or char in UNICODE_BOX_CHARS)
    unicode_count = sum(1 for char in joined if char in UNICODE_BOX_CHARS)
    arrows = len(ARROW_RE.findall(joined))
    long_structured_lines = sum(1 for line in lines if len(line) >= 12 and sum(1 for char in line if char in BOX_CHARS or char in UNICODE_BOX_CHARS) >= 3)

    score = 0
    reasons: list[str] = []
    if unicode_count >= 4:
        score += 4
        reasons.append("unicode box drawing")
    if char_count >= 12:
        score += 3
        reasons.append("dense structural characters")
    if arrows >= 1:
        score += 2
        reasons.append("arrows")
    if long_structured_lines >= 2:
        score += 2
        reasons.append("structured multi-line block")
    if ARCH_WORD_RE.search(joined):
        score += 1
        reasons.append("architecture keywords")
    if FLOW_WORD_RE.search(joined):
        score += 1
        reasons.append("flow keywords")
    return score, reasons


def classify(text: str) -> tuple[str, float, list[str]]:
    score, reasons = diagram_score(text)
    joined = "\n".join(line.rstrip() for line in text.splitlines())
    unicode_count = sum(1 for char in joined if char in UNICODE_BOX_CHARS)
    arrows = len(ARROW_RE.findall(joined))
    sequence_hits = len(SEQUENCE_RE.findall(joined))
    has_arch = bool(ARCH_WORD_RE.search(joined))
    has_flow = bool(FLOW_WORD_RE.search(joined))
    nested_box_hint = unicode_count >= 8 or joined.count("│") >= 4 or joined.count("|") >= 8
    nonempty_lines = [line for line in text.splitlines() if line.strip()]
    header_columns = 0
    if nonempty_lines:
        header_columns = len([part for part in re.split(r"\s{2,}", nonempty_lines[0].strip()) if part])
    lifeline_lines = sum(1 for line in nonempty_lines[:8] if line.count("│") + line.count("|") >= 2)
    participant_sequence_hint = arrows >= 2 and header_columns >= 2 and lifeline_lines >= 1
    state_transition_hint = arrows >= 1 and header_columns < 2 and lifeline_lines == 0

    if participant_sequence_hint or (sequence_hits >= 2 and arrows >= 2 and lifeline_lines >= 1):
        category = "sequence"
        confidence = 0.82
        reasons.append("participant lifelines with message arrows")
    elif nested_box_hint or has_arch:
        category = "architecture"
        confidence = 0.78 if nested_box_hint else 0.64
        reasons.append("container or layer structure")
        if arrows >= 1:
            reasons.append("container diagram with relationships")
    elif state_transition_hint or has_flow:
        category = "flowchart"
        confidence = 0.72 if state_transition_hint else 0.7
        reasons.append("state or directional flow")
    elif arrows >= 1:
        category = "flowchart"
        confidence = 0.7
        reasons.append("directional flow")
    else:
        category = "architecture"
        confidence = 0.5
        reasons.append("fallback for structural text block")

    if score < 4:
        confidence = min(confidence, 0.45)
    return category, confidence, reasons


def main() -> int:
    args = parse_args()
    text = args.markdown.read_text(encoding="utf-8")
    lines = text.splitlines()
    raw_blocks = extract_fenced_blocks(lines)
    if args.include_indented:
        raw_blocks.extend(extract_indented_blocks(lines))

    blocks: list[dict] = []
    for raw in raw_blocks:
        score, score_reasons = diagram_score(raw["content"])
        if score < 4:
            continue
        category, confidence, reasons = classify(raw["content"])
        block = dict(raw)
        block.update(
            {
                "id": f"diagram-{len(blocks) + 1:03d}",
                "category": category,
                "confidence": round(confidence, 2),
                "reasons": sorted(set(score_reasons + reasons)),
            }
        )
        blocks.append(block)

    summary = Counter(block["category"] for block in blocks)
    result = {
        "source": str(args.markdown),
        "blocks": blocks,
        "summary": dict(sorted(summary.items())),
    }
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
