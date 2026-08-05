#!/usr/bin/env python3
"""Log management: list, tail, and prune secauto logs.

Output goes straight to stdout (via print) rather than through the logger,
so that viewing a log never appends to the log file you are viewing.
"""
from __future__ import annotations

import os

import common


def list_logs() -> int:
    log_dir = common.get_log_dir()
    print(f"Log directory: {log_dir}")
    try:
        entries = sorted(os.listdir(log_dir))
    except OSError as exc:
        print(f"Cannot read log dir: {exc}")
        return 1
    logs = [e for e in entries if ".log" in e]
    if not logs:
        print("(no log files yet)")
        return 0
    for name in logs:
        path = os.path.join(log_dir, name)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        print(f"  {name:<24} {size:>9} bytes")
    return 0


def tail_log(name="update.log", lines=40) -> int:
    log_dir = common.get_log_dir()
    path = os.path.join(log_dir, name)
    if not os.path.isfile(path):
        print(f"No such log: {path}")
        return 1
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.readlines()
    except OSError as exc:
        print(f"Cannot read {path}: {exc}")
        return 1
    print(f"--- last {lines} line(s) of {name} ---")
    for line in content[-lines:]:
        print(line.rstrip())
    return 0


def prune_logs(keep=5) -> int:
    """Remove rotated log files (name.log.N) beyond index `keep`.

    The active logs are already size-bounded by RotatingFileHandler; this just
    cleans up any strays.
    """
    log_dir = common.get_log_dir()
    try:
        names = os.listdir(log_dir)
    except OSError as exc:
        print(f"Cannot read log dir: {exc}")
        return 1
    removed = 0
    for name in names:
        if ".log." not in name:
            continue
        try:
            idx = int(name.rsplit(".", 1)[-1])
        except ValueError:
            continue
        if idx > keep:
            try:
                os.remove(os.path.join(log_dir, name))
                removed += 1
            except OSError:
                pass
    print(f"Pruned {removed} old rotated log file(s).")
    return 0


def main() -> int:
    return list_logs()


if __name__ == "__main__":
    raise SystemExit(main())
