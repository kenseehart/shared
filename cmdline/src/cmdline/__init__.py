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
from cmdline.output import emit_output, format_grid, json_dumps

__all__ = [
    "CommandGroup",
    "cmd",
    "cmd_group",
    "cmd_section",
    "cmds",
    "configure_cli_logging",
    "create_parser",
    "emit_output",
    "format_grid",
    "json_dumps",
    "normalize_command_group_subcommand",
    "optarg",
    "run_cli",
    "verbose",
    "_group_flat_aliases",
]
