#!/usr/bin/env python3
"""Run a command with a hard timeout, killing its whole process group.

macOS ships no GNU `timeout`, and plain subprocess timeouts only kill the
direct child (the zcode wrapper), leaving the node process running. This
watchdog starts the command in a new session and SIGKILLs the session leader
on expiry.

Usage: zcode_watchdog.py TIMEOUT_SECONDS LOGFILE -- CMD [ARGS ...]
Exits with the child's exit code, or 124 on timeout (like GNU timeout).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeout', type=float, help='hard timeout in seconds')
    parser.add_argument('logfile', type=Path, help='child stdout/stderr destination')
    parser.add_argument('cmd', nargs=argparse.REMAINDER, help='command after --')
    args = parser.parse_args()
    if args.cmd and args.cmd[0] == '--':
        args.cmd = args.cmd[1:]
    if args.timeout <= 0 or not args.cmd:
        parser.error('expected: TIMEOUT LOGFILE -- CMD [ARGS ...]')
    return args


def kill_group(pid: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pid, signal.SIGKILL)


def main() -> int:
    args = parse_args()

    args.logfile.parent.mkdir(parents=True, exist_ok=True)
    with args.logfile.open('wb') as log_file:
        proc = subprocess.Popen(  # noqa: S603
            args.cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        def _forward_signal(signum: int, _frame: object) -> None:
            # The watchdog got SIGTERM/SIGINT: pass it on, then die with it.
            kill_group(proc.pid)
            sys.exit(128 + signum)

        signal.signal(signal.SIGTERM, _forward_signal)
        signal.signal(signal.SIGINT, _forward_signal)

        deadline = time.monotonic() + args.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                kill_group(proc.pid)
                log_file.write(f'\n[zcode_watchdog] timeout after {args.timeout}s, killed process group\n'.encode())
                return 124
            try:
                return proc.wait(timeout=min(remaining, 5))
            except subprocess.TimeoutExpired:
                continue


if __name__ == '__main__':
    sys.exit(main())
