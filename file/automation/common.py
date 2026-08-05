#!/usr/bin/env python3
"""Shared helpers for the Kali update-automation toolkit (secauto).

Centralises logging, privilege checks, and a subprocess runner so the
update / scan / logs modules all behave consistently.
"""
from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

APP_NAME = "secauto"

# Preferred system-wide log dir; falls back to a per-user dir when not writable.
_SYSTEM_LOG_DIR = "/var/log/secauto"
_USER_LOG_DIR = os.path.expanduser("~/.local/share/secauto/logs")

_LOGGER_CACHE: dict[str, logging.Logger] = {}
_LOG_DIR_CACHE: str | None = None


def is_root() -> bool:
    """True when the current process has root privileges."""
    return hasattr(os, "geteuid") and os.geteuid() == 0


def have_command(name: str) -> bool:
    """True when `name` is found on PATH."""
    return shutil.which(name) is not None


def get_log_dir() -> str:
    """Return a writable log directory, creating it if needed.

    Prefers /var/log/secauto (needs root); otherwise uses a per-user dir;
    last resort is the current working directory.
    """
    global _LOG_DIR_CACHE
    if _LOG_DIR_CACHE is not None:
        return _LOG_DIR_CACHE

    for candidate in (_SYSTEM_LOG_DIR, _USER_LOG_DIR):
        try:
            os.makedirs(candidate, exist_ok=True)
            # Confirm we can actually write here.
            testfile = os.path.join(candidate, ".write-test")
            with open(testfile, "w") as fh:
                fh.write("ok")
            os.remove(testfile)
            _LOG_DIR_CACHE = candidate
            return candidate
        except OSError:
            continue

    _LOG_DIR_CACHE = os.getcwd()
    return _LOG_DIR_CACHE


def get_logger(name: str = APP_NAME) -> logging.Logger:
    """Return a logger that writes to both the console and a rotating file."""
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    # Console handler (INFO and above) -> stdout.
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler (everything), rotating to keep disk usage bounded.
    log_path = os.path.join(get_log_dir(), f"{name}.log")
    try:
        file_handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("Could not open log file %s: %s", log_path, exc)

    _LOGGER_CACHE[name] = logger
    return logger


def _signal_group(proc, sig) -> None:
    """Send `sig` to the child's whole process group, tolerating a dead child.

    Because run() starts children with start_new_session=True, signalling the
    group also reaches grandchildren -- e.g. the real `apt-get` that `sudo`
    spawned -- so a timeout actually frees the dpkg/apt lock instead of
    orphaning a root process.
    """
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except (ProcessLookupError, PermissionError, OSError):
        # Already exited, or no killpg (non-POSIX): fall back to the proc.
        try:
            proc.kill()
        except OSError:
            pass


def run(cmd, logger=None, use_sudo=False, timeout=None) -> int:
    """Run a command (list of args, no shell), streaming + logging its output.

    When `use_sudo` is set and we are not already root, `sudo` is prepended
    (when available). Returns the integer exit code.

    `timeout` (seconds) bounds the *entire* run, including time spent stalled
    mid-output: output is drained on a daemon thread and joined against a
    wall-clock deadline, so a child that hangs while holding its stdout pipe
    open is still killed. On timeout the whole process group is killed (so a
    sudo-wrapped privileged child is reaped too) and 124 is returned.

    NOTE: pass any required environment as an explicit `env VAR=value` prefix
    inside `cmd` -- a Python env= dict would be stripped by sudo's env_reset.
    """
    logger = logger or get_logger()
    cmd = list(cmd)

    if use_sudo and not is_root():
        if have_command("sudo"):
            cmd = ["sudo", *cmd]
        else:
            logger.error("Root required but neither root nor sudo is available.")
            return 1

    logger.info("Running: %s", " ".join(cmd))
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,   # own process group, so we can reap kids
        )
    except FileNotFoundError:
        logger.error("Command not found: %s", cmd[0])
        return 127
    except OSError as exc:
        logger.error("Failed to start %s: %s", cmd[0], exc)
        return 1

    # Drain stdout on a background thread so the main thread can enforce the
    # deadline even if the child stalls without closing its pipe.
    def _drain():
        if proc.stdout is None:
            return
        for line in proc.stdout:
            logger.info(line.rstrip())

    reader = threading.Thread(target=_drain, daemon=True)
    reader.start()

    deadline = (time.monotonic() + timeout) if timeout is not None else None
    try:
        while True:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            try:
                proc.wait(timeout=remaining)
                break
            except subprocess.TimeoutExpired:
                _signal_group(proc, signal.SIGKILL)
                proc.wait()
                reader.join(timeout=2)
                logger.error("Command timed out after %ss: %s", timeout, cmd[0])
                return 124
    except KeyboardInterrupt:
        _signal_group(proc, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _signal_group(proc, signal.SIGKILL)
            proc.wait()
        reader.join(timeout=2)
        logger.warning("Interrupted by user.")
        return 130

    reader.join(timeout=2)
    rc = proc.returncode
    if rc == 0:
        logger.info("OK (exit 0): %s", cmd[0])
    else:
        logger.warning("Exit %s: %s", rc, " ".join(cmd))
    return rc


def banner(logger, title: str) -> None:
    """Log a visual section banner with a timestamp."""
    line = "=" * 60
    logger.info(line)
    logger.info(title)
    logger.info("%s | %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), APP_NAME)
    logger.info(line)
