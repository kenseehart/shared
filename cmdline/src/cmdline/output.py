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


def _resolve_columns(rows: list[dict[str, Any]], columns: list[str] | None) -> list[str]:
    if columns:
        return list(columns)
    seen: set[str] = set()
    resolved: list[str] = []
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                resolved.append(key)
    return resolved


def _project_rows(rows: list[dict[str, Any]], columns: list[str] | None) -> list[dict[str, Any]]:
    if not columns:
        return rows
    return [{col: row.get(col, "") for col in columns} for row in rows]


def _dict_list_table(
    rows: list[dict[str, Any]], *, markdown: bool, columns: list[str] | None = None
) -> list[str]:
    if not rows:
        return ["(empty)"]
    columns = _resolve_columns(rows, columns)
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


def _format_value(
    value: Any, *, markdown: bool, indent: int = 0, columns: list[str] | None = None
) -> list[str]:
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
            lines.extend(
                _format_value(item, markdown=markdown, indent=indent + 1, columns=columns)
            )
        return lines
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            projected = _project_rows(value, columns)
            table_lines = _dict_list_table(projected, markdown=markdown, columns=columns)
            return [f"{prefix}{line}" if not markdown or line.startswith("|") else line for line in table_lines]
        return [f"{prefix}- {_stringify(item)}" for item in value]
    return [f"{prefix}{value!s}"]


def format_grid(
    data: Any,
    *,
    markdown: bool = False,
    title: str | None = None,
    columns: list[str] | None = None,
) -> str:
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
            lines.extend(_format_value(value, markdown=markdown, columns=columns))
    elif isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
        projected = _project_rows(data, columns)
        lines.extend(_dict_list_table(projected, markdown=markdown, columns=columns))
    else:
        lines.extend(_format_value(data, markdown=markdown, columns=columns))
    return "\n".join(lines).rstrip()


def emit_output(
    data: Any,
    *,
    json_output: bool = False,
    md: bool = False,
    title: str | None = None,
    columns: list[str] | None = None,
    file: TextIO | None = None,
) -> None:
    """Print structured command output as JSON or a formatted grid."""
    out = file or sys.stdout
    if json_output:
        payload = _project_rows(data, columns) if isinstance(data, list) and columns else data
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str), file=out)
        return
    print(format_grid(data, markdown=md, title=title, columns=columns), file=out)


def json_dumps(data: Any, *, columns: list[str] | None = None) -> str:
    """JSON for MCP tools and other programmatic callers."""
    payload = _project_rows(data, columns) if isinstance(data, list) and columns else data
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def format_for_agent(
    data: Any,
    *,
    format: str = "text",
    title: str | None = None,
    columns: list[str] | None = None,
) -> str:
    """Format structured data for MCP tools: text (default), md, or json."""
    fmt = format.lower().strip()
    if fmt == "json":
        return json_dumps(data, columns=columns)
    if fmt in ("md", "markdown"):
        return format_grid(data, markdown=True, title=title, columns=columns)
    if fmt not in ("text", "plain", ""):
        raise ValueError(f"Unknown output format: {format!r} (use text, md, or json)")
    return format_grid(data, markdown=False, title=title, columns=columns)


def parse_columns(value: str | None) -> list[str] | None:
    """Parse comma-separated column names; empty/None returns None (all columns)."""
    if not value:
        return None
    cols = [part.strip() for part in value.split(",") if part.strip()]
    return cols or None
