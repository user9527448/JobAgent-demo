"""Deterministic Markdown and safe HTML rendering for daily reports."""

from __future__ import annotations

from html import escape
from typing import Final

from .contracts import DailyReport, DailyReportItem, ReportGroup

_GROUP_TITLES: Final = {
    ReportGroup.PRIORITY_APPLICATIONS: "优先投递",
    ReportGroup.CLOSING_SOON: "即将截止",
    ReportGroup.ADDED_TODAY: "今日新增",
    ReportGroup.NEEDS_CONFIRMATION: "需要确认",
}


def render_markdown(report: DailyReport) -> str:
    """Render one stable, directly readable Markdown report."""
    lines = [
        f"# JOBAGENT 日报 — {report.report_date.isoformat()}",
        "",
        f"> 时区: `{report.timezone}`; 规则版本: `{report.report_version}`。",
        "",
    ]
    for section in report.sections:
        lines.extend((f"## {_GROUP_TITLES[section.group]} ({len(section.items)})", ""))
        if not section.items:
            lines.extend(("本组暂无岗位。", ""))
            continue
        for index, item in enumerate(section.items, start=1):
            lines.extend(_markdown_item(index, item))
    return "\n".join(lines).rstrip() + "\n"


def render_html(report: DailyReport) -> str:
    """Render escaped standalone HTML with only original-source links."""
    sections: list[str] = []
    for section in report.sections:
        title = escape(_GROUP_TITLES[section.group])
        if section.items:
            body = "".join(_html_item(item) for item in section.items)
        else:
            body = "<p>本组暂无岗位。</p>"
        sections.append(f"<section><h2>{title} ({len(section.items)})</h2>{body}</section>")
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        f"<title>JOBAGENT 日报 — {report.report_date.isoformat()}</title></head><body>"
        f"<h1>JOBAGENT 日报 — {report.report_date.isoformat()}</h1>"
        f"<p>时区: <code>{escape(report.timezone)}</code>; 规则版本: "
        f"<code>{escape(report.report_version)}</code>。</p>"
        f"{''.join(sections)}</body></html>"
    )


def _markdown_item(index: int, item: DailyReportItem) -> list[str]:
    risks = "; ".join(_markdown_text(risk) for risk in item.risks)
    return [
        f"### {index}. {_markdown_text(_display(item.title))}",
        "",
        f"- 单位: {_markdown_text(_display(item.organization))}",
        f"- 地区: {_markdown_text(_display(item.region))}",
        f"- 截止: {_markdown_text(_display(_deadline(item)))}",
        f"- 评分: {item.score}/100",
        f"- 理由: {_markdown_text(item.reason)}",
        f"- 风险: {risks}",
        f"- 原文: <{_markdown_url(item.source_url)}>",
        "",
    ]


def _html_item(item: DailyReportItem) -> str:
    risks = "".join(f"<li>{escape(risk)}</li>" for risk in item.risks)
    url = escape(item.source_url, quote=True)
    return (
        f"<article><h3>{escape(_display(item.title))}</h3><ul>"
        f"<li>单位: {escape(_display(item.organization))}</li>"
        f"<li>地区: {escape(_display(item.region))}</li>"
        f"<li>截止: {escape(_display(_deadline(item)))}</li>"
        f"<li>评分: {item.score}/100</li>"
        f"<li>理由: {escape(item.reason)}</li>"
        f"<li>风险: <ul>{risks}</ul></li>"
        f'</ul><p><a href="{url}" rel="noopener noreferrer">查看原文</a></p></article>'
    )


def _deadline(item: DailyReportItem) -> str | None:
    return item.deadline.isoformat() if item.deadline is not None else None


def _display(value: str | None) -> str:
    return value if value is not None and value.strip() else "未提供 (需确认)"


def _markdown_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ("`", "*", "_", "[", "]", "<", ">"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _markdown_url(value: str) -> str:
    return value.replace("<", "%3C").replace(">", "%3E")
