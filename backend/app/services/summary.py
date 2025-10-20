from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List

from ..schemas import SummaryRequest, SummaryResponse

MAX_CHARACTERS = 1000

SECTION_HEADERS = {
    "purpose": ["目的", "ゴール", "狙い", "目標"],
    "decisions": ["決定", "合意", "決めた", "承認"],
    "action_items": ["宿題", "アクション", "TODO", "タスク", "対応"],
    "digest": ["概要", "要旨", "サマリ", "まとめ", "ポイント"],
}

BULLET_PATTERN = re.compile(r"^[-*・\d\.\)]\s*")


@dataclass
class ParsedSections:
    purpose: List[str]
    decisions: List[str]
    action_items: List[str]
    digest: List[str]
    remainder: List[str]


def parse_text(request: SummaryRequest) -> ParsedSections:
    lines = [line.strip() for line in request.text.splitlines() if line.strip()]
    sections: Dict[str, List[str]] = {k: [] for k in ["purpose", "decisions", "action_items", "digest"]}
    remainder: List[str] = []

    current_key = None
    for line in lines:
        normalized = line.replace("：", ":").replace("-", "-")
        lower_line = normalized.lower()
        matched = False
        for key, keywords in SECTION_HEADERS.items():
            if any(keyword.lower() in lower_line for keyword in keywords):
                current_key = key
                cleaned = re.split(r"[:：]\s*", line, maxsplit=1)
                if len(cleaned) == 2:
                    sections[key].append(cleaned[1].strip())
                else:
                    sections[key].append(line)
                matched = True
                break
        if matched:
            continue
        if current_key:
            sections[current_key].append(line)
        elif request.input_mode == "bullet" and BULLET_PATTERN.match(line):
            sections["digest"].append(BULLET_PATTERN.sub("", line))
        else:
            remainder.append(line)

    return ParsedSections(
        purpose=sections["purpose"],
        decisions=sections["decisions"],
        action_items=sections["action_items"],
        digest=sections["digest"],
        remainder=remainder,
    )


def _join_lines(lines: Iterable[str]) -> str:
    return "\n".join(line.strip() for line in lines if line.strip())


def fallback_digest(parsed: ParsedSections) -> List[str]:
    if parsed.digest:
        return parsed.digest
    # if no digest provided, use remainder or decisions/purpose
    candidates = list(itertools.islice(parsed.remainder, 0, 3))
    if not candidates:
        candidates = list(itertools.islice(parsed.decisions or parsed.purpose, 0, 3))
    return candidates


def summarize(request: SummaryRequest) -> SummaryResponse:
    parsed = parse_text(request)

    purpose = _join_lines(parsed.purpose) or infer_purpose(request, parsed)
    decisions = _join_lines(parsed.decisions) or infer_decisions(parsed)
    action_items = _join_lines(parsed.action_items) or infer_actions(parsed)
    digest_lines = fallback_digest(parsed)
    digest = _join_lines(digest_lines) or purpose

    summary_text = {"purpose": purpose, "decisions": decisions, "action_items": action_items, "digest": digest}
    total_chars = sum(len(v) for v in summary_text.values())

    if total_chars > MAX_CHARACTERS:
        summary_text = truncate_sections(summary_text, MAX_CHARACTERS)
        total_chars = sum(len(v) for v in summary_text.values())

    return SummaryResponse(total_characters=total_chars, **summary_text)


def infer_purpose(request: SummaryRequest, parsed: ParsedSections) -> str:
    if parsed.remainder:
        return parsed.remainder[0]
    return f"{request.title}に関する会議の目的を確認" if request.title else "会議の目的を要約"


def infer_decisions(parsed: ParsedSections) -> str:
    if parsed.remainder:
        return "\n".join(parsed.remainder[1:3])
    return "決定事項は会議内の合意内容に基づきます"


def infer_actions(parsed: ParsedSections) -> str:
    if parsed.decisions:
        return "\n".join(parsed.decisions[-2:])
    return "宿題は会議参加者に共有済みのタスクを参照してください"


def truncate_sections(sections: Dict[str, str], limit: int) -> Dict[str, str]:
    keys = list(sections.keys())
    lengths = [len(sections[k]) for k in keys]
    total = sum(lengths)
    if total <= limit:
        return sections

    # proportionally truncate while preserving essential info
    truncated: Dict[str, str] = {}
    for key in keys:
        value = sections[key]
        if not value:
            truncated[key] = value
            continue
        share = max(int(limit * (len(value) / total)), min(80, limit // len(keys)))
        truncated[key] = value[:share].rstrip()
    return truncated
