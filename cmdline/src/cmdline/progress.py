"""tqdm progress bars that coexist cleanly with logging and other stdout/stderr output."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any, Iterator, TextIO

from tqdm import tqdm

# Clear to end of line — reset cursor before non-tqdm writes so log lines do not
# append to the active progress bar on the same terminal row.
_CLEAR_LINE = "\r\033[K"


class _ProgressSafeStream:
    """Wrap a text stream so foreign writes do not collide with tqdm's \\r bar."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def write(self, s: str) -> int:
        if not s:
            return self._stream.write(s)
        if s.startswith("\r") or s.startswith("\x1b["):
            return self._stream.write(s)
        self._stream.write(_CLEAR_LINE)
        return self._stream.write(s)

    def flush(self) -> None:
        self._stream.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


@contextmanager
def progress_session(*, disable: bool = False) -> Iterator[None]:
    """Patch stdout/stderr while progress bars are active; restore on exit."""
    if disable:
        yield
        return

    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    sys.stdout = _ProgressSafeStream(orig_stdout)  # type: ignore[assignment]
    sys.stderr = _ProgressSafeStream(orig_stderr)  # type: ignore[assignment]
    try:
        yield
    finally:
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr


def progress_bar(*args: Any, **kwargs: Any) -> tqdm:
    """tqdm bar — use inside :func:`progress_session`."""
    return tqdm(*args, **kwargs)


def progress_write(msg: str, *, file: TextIO | None = None) -> None:
    """Print a line without corrupting active progress bars."""
    tqdm.write(msg, file=file)
