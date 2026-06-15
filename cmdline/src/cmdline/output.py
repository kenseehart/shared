from __future__ import annotations

import json
import sys
from typing import Any, TextIO

_SCALAR_TYPES = (str, int, float, bool, type(None))


def _is_scalar(value: Any) -> bool:
    return isinstance(value, _SCALAR_TYPES)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _heading(text: str, markdown: bool) -> str:
    label = text.replace("_", " ")
    return f"## {label}" if markdown else f"{label}:"


def _kv_table(items: dict[str, Any], *, markdown: bool) -> list[str]:
    if not items:
        return []
    rows = [(key, _stringify(value)) for key, value in items.items()]
    if markdown:
        lines = ["| key | value |", "| --- | --- |"]
        lines.extend(f"| {key} | {value} |" for key, value in rows)
        return lines
    width = max(len(key) for key, _ in rows)
    return [f"{key:<{width}}  {value}" for key, value in rows]


def _dict_list_table(rows: list[dict[str, Any]], *, markdown: bool) -> list[str]:
    if not rows:
        return ["(empty)"]
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)
    if markdown:
        header = "| " + " | ".join(columns) + " |"
        sep = "| " + " | ".join("---" for _ in columns) + " |"
        body = [
            "| " + " | ".join(_stringify(row.get(col, "")) for col in columns) + " |"
            for row in rows
        ]
        return [header, sep, *body]
    widths = {
        col: max(len(col), *(len(_stringify(row.get(col, ""))) for row in rows))
        for col in columns
    }
    header = "  ".join(col.ljust(widths[col]) for col in columns)
    divider = "  ".join("-" * widths[col] for col in columns)
    body = [
        "  ".join(_stringify(row.get(col, "")).ljust(widths[col]) for col in columns)
        for row in rows
    ]
    return [header, divider, *body]


def _format_value(value: Any, *, markdown: bool, indent: int = 0) -> list[str]:
    prefix = "  " * indent
    if _is_scalar(value):
        return [f"{prefix}{_stringify(value)}"]
    if isinstance(value, dict):
        lines: list[str] = []
        scalars = {k: v for k, v in value.items() if _is_scalar(v)}
        nested = {k: v for k, v in value.items() if not _is_scalar(v)}
        if scalars:
            for line in _kv_table(scalars, markdown=markdown):
                lines.append(f"{prefix}{line}" if not markdown or line.startswith("|") else line)
        for key, item in nested.items():
            lines.append(f"{prefix}{_heading(key, markdown)}")
            lines.extend(_format_value(item, markdown=markdown, indent=indent + 1))
        return lines
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            table_lines = _dict_list_table(value, markdown=markdown)
            return [f"{prefix}{line}" if not markdown or line.startswith("|") else line for line in table_lines]
        return [f"{prefix}- {_stringify(item)}" for item in value]
    return [f"{prefix}{value!s}"]


def format_grid(data: Any, *, markdown: bool = False, title: str | None = None) -> str:
    """Render structured data as a human-readable grid (plain text or markdown)."""
    lines: list[str] = []
    if title:
        lines.append(f"# {title}" if markdown else title)
        lines.append("")
    if isinstance(data, dict):
        scalars = {k: v for k, v in data.items() if _is_scalar(v)}
        nested = {k: v for k, v in data.items() if not _is_scalar(v)}
        if scalars:
            lines.extend(_kv_table(scalars, markdown=markdown))
        for key, value in nested.items():
            if lines:
                lines.append("")
            lines.append(_heading(key, markdown))
            lines.extend(_format_value(value, markdown=markdown))
    elif isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
        lines.extend(_dict_list_table(data, markdown=markdown))
    else:
        lines.extend(_format_value(data, markdown=markdown))
    return "\n".join(lines).rstrip()


def emit_output(
    data: Any,
    *,
    json_output: bool = False,
    md: bool = False,
    title: str | None = None,
    file: TextIO | None = None,
) -> None:
    """Print structured command output as JSON or a formatted grid."""
    out = file or sys.stdout
    if json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str), file=out)
        return
    print(format_grid(data, markdown=md, title=title), file=out)


def json_dumps(data: Any) -> str:
    """JSON for MCP tools and other programmatic callers."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)
