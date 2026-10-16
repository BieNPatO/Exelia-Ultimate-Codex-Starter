"""Bounded subprocess execution for quality-gated checkpoints and integration tests."""
from __future__ import annotations

import os
import signal
import subprocess
import threading


def timeout_budget(variable: str, default: int) -> int:
    """Configuration is explicit seconds, bounded to avoid accidental unlimited waits."""
    value = os.environ.get(variable, str(default))
    if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 7200:
        raise ValueError(f'{variable} must be an integer number of seconds between 1 and 7200')
    return int(value)


def run_group(args: list[str], *, timeout: int, cwd, env=None, interrupt_first: bool = False) -> subprocess.CompletedProcess:
    """Kill the entire session on deadline/interruption so a child cannot commit later."""
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('Process supervision requires the main thread for safe SIGTERM cleanup')
    process = None
    terminated = False

    def terminate(signum, _frame):
        nonlocal terminated
        terminated = True
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if process is not None:
            raise SystemExit(128 + signum)

    previous_handler = signal.signal(signal.SIGTERM, terminate)
    try:
        with subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              start_new_session=True) as process:
            try:
                if terminated:
                    raise SystemExit(128 + signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=timeout)
            except BaseException:
                try:
                    if interrupt_first and process.poll() is None:
                        # The smoke wrapper interrupts Python so its nested checkpoint is reaped first.
                        try:
                            process.send_signal(signal.SIGINT)
                        except ProcessLookupError:
                            pass
                        try:
                            process.communicate(timeout=2)
                        except subprocess.TimeoutExpired:
                            pass
                finally:
                    # SIGKILL prevents a shell trap or surviving gate child from creating a late commit.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    try:
                        process.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        # An independently detached descendant must not hold our pipe cleanup open.
                        process.stdout.close()
                        process.stderr.close()
                        process.wait(timeout=2)
                raise
            return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
