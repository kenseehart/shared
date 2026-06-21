from __future__ import annotations

import argparse
import inspect
import logging
import sys
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, get_args, get_origin, get_type_hints

logger = logging.getLogger(__name__)

_MISSING = object()


@dataclass
class OptArg:
    """Metadata for a CLI parameter — use as default value in @cmd function signatures."""

    default: Any = _MISSING
    help: str = ""
    metavar: str | None = None
    choices: list[Any] | tuple[Any, ...] | None = None
    type: type | None = None
    flag: str | None = None
    long_flag: str | None = None
    action: str | None = None
    nargs: str | None = None
    hidden: bool = False
    required: bool = False
    positional: bool = False
    dest: str | None = None


def optarg(
    default: Any = _MISSING,
    *,
    help: str = "",
    metavar: str | None = None,
    choices: Iterable[Any] | None = None,
    type: type | None = None,
    flag: str | None = None,
    long_flag: str | None = None,
    action: str | None = None,
    nargs: str | None = None,
    hidden: bool = False,
    required: bool = False,
    positional: bool = False,
    dest: str | None = None,
) -> OptArg:
    return OptArg(
        default=default,
        help=help,
        metavar=metavar,
        choices=list(choices) if choices is not None else None,
        type=type,
        flag=flag,
        long_flag=long_flag,
        action=action,
        nargs=nargs,
        hidden=hidden,
        required=required,
        positional=positional,
        dest=dest,
    )


verbose = optarg(
    False,
    flag="-v",
    long_flag="--verbose",
    action="store_true",
    help="Verbose logging",
)


@dataclass
class Cmd:
    fn: Callable[..., Any]
    name: str
    help: str
    aliases: list[str] = field(default_factory=list)
    hidden: bool = False
    group: str | None = None
    section: str | None = None
    output: bool = False


_CMD_ATTR = "_cmdline_cmd"
_GROUP_ATTR = "_cmdline_group"
_SECTION_ATTR = "_cmdline_section"


def cmd(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    aliases: list[str] | None = None,
    hidden: bool = False,
    output: bool = False,
) -> Callable[..., Any]:
    def decorate(f: Callable[..., Any]) -> Callable[..., Any]:
        meta = Cmd(
            fn=f,
            name=name or f.__name__.replace("_", "-"),
            help=(inspect.getdoc(f) or "").strip().split("\n")[0],
            aliases=aliases or [],
            hidden=hidden,
            output=output,
        )
        setattr(f, _CMD_ATTR, meta)
        return f

    if fn is not None:
        return decorate(fn)
    return decorate


def cmd_group(name: str, *, help: str = "") -> CommandGroup:
    return CommandGroup(name, help=help)


def cmd_section(name: str) -> str:
    return name


class CommandGroup:
    def __init__(self, name: str, *, help: str = "") -> None:
        self.name = name
        self.help = help
        self.commands: list[Cmd] = []

    def cmd(
        self,
        fn: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        aliases: list[str] | None = None,
        hidden: bool = False,
        output: bool = False,
    ) -> Callable[..., Any]:
        def decorate(f: Callable[..., Any]) -> Callable[..., Any]:
            decorated = cmd(name=name, aliases=aliases, hidden=hidden, output=output)(f)
            meta: Cmd = getattr(decorated, _CMD_ATTR)
            meta.group = self.name
            self.commands.append(meta)
            setattr(decorated, _GROUP_ATTR, self)
            return decorated

        if fn is not None:
            return decorate(fn)
        return decorate


def cmds(module: types.ModuleType | Any) -> list[Cmd]:
    found: list[Cmd] = []
    for value in vars(module).values():
        meta = getattr(value, _CMD_ATTR, None)
        if isinstance(meta, Cmd):
            found.append(meta)
    found.sort(key=lambda c: c.name)
    return found


def _group_flat_aliases(group: CommandGroup) -> dict[str, str]:
    return {alias: cmd.name for cmd in group.commands for alias in cmd.aliases}


def normalize_command_group_subcommand(argv: list[str], groups: list[CommandGroup]) -> list[str]:
    if len(argv) < 2:
        return argv
    group_names = {g.name for g in groups}
    if argv[1] not in group_names:
        return argv
    if len(argv) < 3:
        return argv
    aliases = {}
    for group in groups:
        if group.name == argv[1]:
            aliases = _group_flat_aliases(group)
            break
    if argv[2] in aliases:
        argv = argv[:2] + [aliases[argv[2]]] + argv[3:]
    return argv


def _unwrap_optarg(value: Any) -> tuple[Any, OptArg | None]:
    if isinstance(value, OptArg):
        return value.default, value
    return value, None


def _is_optional_param(default: Any) -> bool:
    if isinstance(default, OptArg):
        return True
    return default is not inspect.Parameter.empty


def _python_type_to_argparse(annotation: Any) -> type | None:
    if annotation is inspect.Parameter.empty:
        return None
    origin = get_origin(annotation)
    if origin is None:
        if annotation in (bool, int, float, str):
            return annotation
        return None
    if origin is types.UnionType:
        args = [a for a in get_args(annotation) if a is not type(None)]
        return _python_type_to_argparse(args[0]) if args else None
    return None


def _add_param_to_parser(
    parser: argparse.ArgumentParser,
    param_name: str,
    param: inspect.Parameter,
    opt_meta: OptArg | None,
    type_hints: dict[str, Any],
) -> None:
    annotation = type_hints.get(param_name, param.annotation)
    default, opt_meta = _unwrap_optarg(param.default)
    is_optional = _is_optional_param(param.default)
    py_type = (opt_meta.type if opt_meta and opt_meta.type else None) or _python_type_to_argparse(
        annotation
    )

    if opt_meta and opt_meta.positional:
        kwargs = {"help": opt_meta.help}
        if opt_meta.metavar:
            kwargs["metavar"] = opt_meta.metavar
        if opt_meta.choices:
            kwargs["choices"] = opt_meta.choices
        if py_type is not None:
            kwargs["type"] = py_type
        if opt_meta.nargs:
            kwargs["nargs"] = opt_meta.nargs
        elif default is _MISSING or opt_meta.required:
            pass
        else:
            kwargs["nargs"] = "?"
            kwargs["default"] = default
        parser.add_argument(param_name, **kwargs)
        return

    if opt_meta and opt_meta.action == "store_true":
        flags = []
        if opt_meta.flag:
            flags.append(opt_meta.flag)
        if opt_meta.long_flag:
            flags.append(opt_meta.long_flag)
        if not flags:
            flags = [f"--{param_name.replace('_', '-')}"]
        parser.add_argument(
            *flags,
            action="store_true",
            default=False if default is _MISSING else bool(default),
            help=opt_meta.help,
        )
        return

    if is_optional:
        flags = []
        if opt_meta and opt_meta.flag:
            flags.append(opt_meta.flag)
        long_flag = (opt_meta.long_flag if opt_meta else None) or f"--{param_name.replace('_', '-')}"
        flags.append(long_flag)
        kwargs: dict[str, Any] = {"help": opt_meta.help if opt_meta else ""}
        if opt_meta and opt_meta.metavar:
            kwargs["metavar"] = opt_meta.metavar
        if opt_meta and opt_meta.dest:
            kwargs["dest"] = opt_meta.dest
        if opt_meta and opt_meta.choices:
            kwargs["choices"] = opt_meta.choices
        if py_type is not None:
            kwargs["type"] = py_type
        if opt_meta and opt_meta.nargs:
            kwargs["nargs"] = opt_meta.nargs
        if opt_meta and opt_meta.required:
            kwargs["required"] = True
        elif default is not _MISSING:
            kwargs["default"] = default
        parser.add_argument(*flags, **kwargs)
        return

    kwargs = {"help": opt_meta.help if opt_meta else ""}
    if opt_meta and opt_meta.metavar:
        kwargs["metavar"] = opt_meta.metavar
    if py_type is not None:
        kwargs["type"] = py_type
    if opt_meta and opt_meta.choices:
        kwargs["choices"] = opt_meta.choices
    parser.add_argument(param_name, **kwargs)


_OUTPUT_PARAMS = ("json_output", "md_output")


def _add_output_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output JSON",
    )
    parser.add_argument(
        "--md",
        action="store_true",
        dest="md_output",
        help="Markdown grid output (default: plain-text grid)",
    )


def _bind_and_call(cmd_meta: Cmd, args: argparse.Namespace) -> Any:
    sig = inspect.signature(cmd_meta.fn)
    bound: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name in _OUTPUT_PARAMS:
            continue
        default, opt_meta = _unwrap_optarg(param.default)
        if hasattr(args, name):
            value = getattr(args, name)
            if isinstance(param.default, OptArg) and param.default.action == "store_true":
                bound[name] = bool(value)
            else:
                bound[name] = value
        elif opt_meta is not None:
            bound[name] = None if default is _MISSING else default
        elif default is not inspect.Parameter.empty:
            bound[name] = default
    for name in _OUTPUT_PARAMS:
        if name in sig.parameters and name not in bound:
            bound[name] = bool(getattr(args, name, False))
    return cmd_meta.fn(**bound)


def create_parser(
    commands: list[Cmd],
    *,
    prog: str,
    description: str = "",
    groups: list[CommandGroup] | None = None,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    sub = parser.add_subparsers(dest="_subcommand", required=True)

    grouped: dict[str | None, list[Cmd]] = {}
    for command in commands:
        grouped.setdefault(command.group, []).append(command)

    for group_name, group_cmds in grouped.items():
        if group_name:
            group_help = next((g.help for g in (groups or []) if g.name == group_name), "")
            parent = sub.add_parser(group_name, help=group_help)
            nested = parent.add_subparsers(dest="_subcommand", required=True)
            target = nested
        else:
            target = sub

        for command in group_cmds:
            cmd_parser = target.add_parser(
                command.name,
                help=command.help,
                aliases=command.aliases,
            )
            sig = inspect.signature(command.fn)
            hints = get_type_hints(command.fn)
            for pname, param in sig.parameters.items():
                if pname in ("verbose", *_OUTPUT_PARAMS):
                    continue
                opt_meta = param.default if isinstance(param.default, OptArg) else None
                _add_param_to_parser(cmd_parser, pname, param, opt_meta, hints)
            if command.output:
                _add_output_flags(cmd_parser)
            cmd_parser.set_defaults(_cmd_meta=command)

    return parser


def configure_cli_logging(verbose_enabled: bool) -> None:
    level = logging.INFO if verbose_enabled else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        force=True,
    )
    for name in ("httpx", "httpcore", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)


def run_cli(
    parser: argparse.ArgumentParser,
    argv: list[str] | None = None,
    *,
    groups: list[CommandGroup] | None = None,
) -> int:
    argv = list(argv if argv is not None else sys.argv)
    if groups:
        argv = normalize_command_group_subcommand(argv, groups)
    args = parser.parse_args(argv[1:])
    configure_cli_logging(getattr(args, "verbose", False))
    cmd_meta: Cmd | None = getattr(args, "_cmd_meta", None)
    if cmd_meta is None:
        parser.error("No command selected")
    try:
        result = _bind_and_call(cmd_meta, args)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    if result is None:
        return 0
    if isinstance(result, bool):
        return 0 if result else 1
    if isinstance(result, int):
        return result
    return 0
