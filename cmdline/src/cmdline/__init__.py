"""Decorator-driven argparse CLI — declare commands on functions with @cmd."""

from cmdline.core import (
    CommandGroup,
    cmd,
    cmd_group,
    cmd_section,
    cmds,
    configure_cli_logging,
    create_parser,
    normalize_command_group_subcommand,
    optarg,
    run_cli,
    verbose,
    _group_flat_aliases,
)
from cmdline.output import emit_output, format_for_agent, format_grid, json_dumps, parse_columns
from cmdline.progress import progress_bar, progress_session, progress_write

__all__ = [
    "CommandGroup",
    "cmd",
    "cmd_group",
    "cmd_section",
    "cmds",
    "configure_cli_logging",
    "create_parser",
    "emit_output",
    "format_for_agent",
    "format_grid",
    "json_dumps",
    "parse_columns",
    "normalize_command_group_subcommand",
    "optarg",
    "progress_bar",
    "progress_session",
    "progress_write",
    "run_cli",
    "verbose",
    "_group_flat_aliases",
]
