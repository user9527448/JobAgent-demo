"""Deterministic PushPlus-sized rendering of immutable daily reports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

from jobagent.reports import DailyReportSnapshot

from .contracts import DeliveryChannel, DeliveryMessage, DeliveryMessagePart

CURRENT_DELIVERY_VERSION: Final = "jai-027-v1"
PUSHPLUS_BODY_CHAR_LIMIT: Final = 18_000
PUSHPLUS_TITLE_CHAR_LIMIT: Final = 90


@dataclass(frozen=True, slots=True)
class DeterministicDeliveryRenderer:
    """Split Markdown on semantic boundaries with stable hashes and ordering."""

    body_char_limit: int = PUSHPLUS_BODY_CHAR_LIMIT
    title_char_limit: int = PUSHPLUS_TITLE_CHAR_LIMIT
    delivery_version: str = CURRENT_DELIVERY_VERSION

    def __post_init__(self) -> None:
        if self.body_char_limit <= 0 or self.body_char_limit > PUSHPLUS_BODY_CHAR_LIMIT:
            raise ValueError("Delivery body limit must be within the PushPlus safety cap.")
        if self.title_char_limit <= 0 or self.title_char_limit > PUSHPLUS_TITLE_CHAR_LIMIT:
            raise ValueError("Delivery title limit must be within the PushPlus safety cap.")
        if not self.delivery_version.strip():
            raise ValueError("Delivery version cannot be empty.")

    def render(self, snapshot: DailyReportSnapshot) -> DeliveryMessage:
        """Render the same message and hashes for the same immutable snapshot."""
        if snapshot.id <= 0:
            raise ValueError("Delivery requires a persisted report snapshot.")
        if not snapshot.markdown.strip():
            raise ValueError("Delivery requires non-empty report Markdown.")

        contents = _pack_blocks(_semantic_blocks(snapshot.markdown), self.body_char_limit)
        part_count = len(contents)
        parts: list[DeliveryMessagePart] = []
        for index, content in enumerate(contents, start=1):
            title = (
                f"JOBAGENT 日报 {snapshot.report.report_date.isoformat()} [{index}/{part_count}]"
            )
            if len(title) > self.title_char_limit:
                raise ValueError("Rendered delivery title exceeds the configured safety cap.")
            parts.append(
                DeliveryMessagePart(
                    part_number=index,
                    part_count=part_count,
                    title=title,
                    content=content,
                    content_hash=_sha256(content),
                )
            )

        message_hash = _sha256(
            json.dumps(
                {
                    "report_snapshot_id": snapshot.id,
                    "report_content_hash": snapshot.content_hash,
                    "channel": DeliveryChannel.PUSHPLUS_WECHAT.value,
                    "delivery_version": self.delivery_version,
                    "parts": [
                        {
                            "part_number": part.part_number,
                            "title": part.title,
                            "content_hash": part.content_hash,
                        }
                        for part in parts
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return DeliveryMessage(
            report_snapshot_id=snapshot.id,
            report_content_hash=snapshot.content_hash,
            channel=DeliveryChannel.PUSHPLUS_WECHAT,
            delivery_version=self.delivery_version,
            message_hash=message_hash,
            parts=tuple(parts),
        )


def _semantic_blocks(markdown: str) -> tuple[str, ...]:
    lines = markdown.splitlines(keepends=True)
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if current and line.startswith(("## ", "### ")):
            blocks.append("".join(current))
            current = []
        current.append(line)
    if current:
        blocks.append("".join(current))
    return tuple(blocks)


def _pack_blocks(blocks: tuple[str, ...], limit: int) -> tuple[str, ...]:
    parts: list[str] = []
    current = ""
    for block in blocks:
        for unit in _bounded_units(block, limit):
            if current and len(current) + len(unit) > limit:
                parts.append(current)
                current = ""
            current += unit
    if current:
        parts.append(current)
    if not parts:
        raise ValueError("Delivery rendering produced no message parts.")
    return tuple(parts)


def _bounded_units(block: str, limit: int) -> tuple[str, ...]:
    if len(block) <= limit:
        return (block,)
    units: list[str] = []
    current = ""
    for line in block.splitlines(keepends=True):
        if len(line) > limit:
            if current:
                units.append(current)
                current = ""
            units.extend(line[index : index + limit] for index in range(0, len(line), limit))
            continue
        if current and len(current) + len(line) > limit:
            units.append(current)
            current = ""
        current += line
    if current:
        units.append(current)
    return tuple(units)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
