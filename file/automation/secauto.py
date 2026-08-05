#!/usr/bin/env python3
"""secauto -- Kali update-automation dispatcher.

This is the Python backend invoked by the C launcher (security.c), but it is
also fully usable on its own:

    python3 secauto.py update
    python3 secauto.py scan --deep
    python3 secauto.py logs tail --lines 60
    python3 secauto.py all
"""
from __future__ import annotations

import argparse
import os
import sys

# Make sibling modules importable no matter how we are launched.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common      # noqa: E402
import update      # noqa: E402
import scan        # noqa: E402
import logs        # noqa: E402
import schedule    # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="secauto",
        description="Kali update & security automation",
    )
    sub = p.add_subparsers(dest="command", required=True)

    up = sub.add_parser("update", help="update & upgrade packages")
    up.add_argument("--no-full", action="store_true",
                    help="use 'upgrade' instead of 'full-upgrade'")
    up.add_argument("--no-clean", action="store_true",
                    help="skip autoremove/autoclean")

    sc = sub.add_parser("scan", help="run a read-only local security audit")
    sc.add_argument("--deep", action="store_true",
                    help="also run lynis/rkhunter when installed")

    lg = sub.add_parser("logs", help="manage logs")
    lg.add_argument("action", nargs="?", default="list",
                    choices=["list", "tail", "prune"])
    lg.add_argument("--name", default="update.log",
                    help="log file for 'tail' (default: update.log; "
                         "loggers are named update/scan)")
    lg.add_argument("--lines", type=int, default=40,
                    help="number of lines for 'tail' (default: 40)")

    sub.add_parser("all", help="run update then scan")

    # Scheduling: enable/stop the every-7-hours systemd timer.
    sub.add_parser("schedule-enable",
                   help="enable automatic updates every 7 hours")
    sub.add_parser("schedule-stop",
                   help="stop/disable the automatic 7-hour updates")
    sub.add_parser("schedule-status",
                   help="show when the next automatic update will run")
    return p


def cmd_update(args) -> int:
    return update.run_update(
        common.get_logger("update"),
        full=not args.no_full,
        autoremove=not args.no_clean,
        clean=not args.no_clean,
    )


def cmd_scan(args) -> int:
    return scan.run_scan(common.get_logger("scan"), deep=args.deep)


def cmd_logs(args) -> int:
    if args.action == "tail":
        return logs.tail_log(args.name, args.lines)
    if args.action == "prune":
        return logs.prune_logs()
    return logs.list_logs()


def cmd_all(args) -> int:
    rc_update = update.run_update(common.get_logger("update"))
    rc_scan = scan.run_scan(common.get_logger("scan"))
    return rc_update or rc_scan


def cmd_schedule_enable(args) -> int:
    return schedule.enable_timer(common.get_logger("schedule"))


def cmd_schedule_stop(args) -> int:
    return schedule.disable_timer(common.get_logger("schedule"))


def cmd_schedule_status(args) -> int:
    return schedule.status_timer(common.get_logger("schedule"))


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    dispatch = {
        "update": cmd_update,
        "scan": cmd_scan,
        "logs": cmd_logs,
        "all": cmd_all,
        "schedule-enable": cmd_schedule_enable,
        "schedule-stop": cmd_schedule_stop,
        "schedule-status": cmd_schedule_status,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
