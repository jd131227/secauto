#!/usr/bin/env python3
"""Schedule management: enable/stop the every-7-hours update timer.

This module makes the C menu's options 5 (enable) and 6 (stop) self-contained:
it generates the systemd .service/.timer units on the fly -- pointing
ExecStart at wherever this very secauto.py lives -- installs them into
/etc/systemd/system, and drives systemctl. No separate `cp` step needed.

Needs root; when not root, the systemctl/install calls go through sudo (so
you'll be prompted for a password if you launched the menu as a normal user).
"""
from __future__ import annotations

import os
import sys
import tempfile

import common

SYSTEMD_DIR = "/etc/systemd/system"
SERVICE_NAME = "secauto-update.service"
TIMER_NAME = "secauto-update.timer"
INTERVAL = "7h"          # change here to retune the cadence


def _secauto_script() -> str:
    """Absolute path to secauto.py (the dispatcher) next to this module."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "secauto.py"))


def _python() -> str:
    """Interpreter to bake into ExecStart (fall back to the usual path)."""
    return sys.executable or "/usr/bin/python3"


def _service_unit() -> str:
    return (
        "[Unit]\n"
        "Description=secauto automated APT update\n"
        "Wants=network-online.target\n"
        "After=network-online.target\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        "User=root\n"
        f"ExecStart={_python()} {_secauto_script()} update\n"
        "ProtectHome=read-only\n"
    )


def _timer_unit() -> str:
    return (
        "[Unit]\n"
        f"Description=Run secauto update every {INTERVAL}\n"
        "\n"
        "[Timer]\n"
        "# First run 10 min after boot, then a fixed interval after each run.\n"
        "OnBootSec=10min\n"
        f"OnUnitActiveSec={INTERVAL}\n"
        "RandomizedDelaySec=10min\n"
        "Persistent=true\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def _write_unit(name: str, content: str, logger) -> int:
    """Stage `content` in a temp file, then install it (root) into systemd."""
    dest = os.path.join(SYSTEMD_DIR, name)
    try:
        fd, tmp = tempfile.mkstemp(suffix=".unit")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
    except OSError as exc:
        logger.error("Could not stage unit file %s: %s", name, exc)
        return 1

    # `install` copies with the right mode and elevates via sudo when needed.
    rc = common.run(["install", "-m", "0644", tmp, dest],
                    logger=logger, use_sudo=True)
    try:
        os.remove(tmp)
    except OSError:
        pass

    if rc == 0:
        logger.info("Installed %s", dest)
    else:
        logger.error("Failed to install %s (rc=%s)", dest, rc)
    return rc


def enable_timer(logger=None) -> int:
    """Menu option 5: install units and start the every-7-hours timer."""
    logger = logger or common.get_logger("schedule")
    common.banner(logger, f"ENABLE {INTERVAL.upper()} UPDATE AUTOMATION")

    if not common.have_command("systemctl"):
        logger.error("systemctl not found -- needs a systemd host (Kali/Debian).")
        return 1

    if _write_unit(SERVICE_NAME, _service_unit(), logger):
        return 1
    if _write_unit(TIMER_NAME, _timer_unit(), logger):
        return 1

    common.run(["systemctl", "daemon-reload"], logger=logger, use_sudo=True)
    rc = common.run(["systemctl", "enable", "--now", TIMER_NAME],
                    logger=logger, use_sudo=True)
    if rc == 0:
        logger.info("Enabled. Updates will run every %s.", INTERVAL)
        common.run(["systemctl", "list-timers", TIMER_NAME, "--no-pager"],
                   logger=logger, use_sudo=True)
    else:
        logger.error("Could not enable %s (rc=%s).", TIMER_NAME, rc)
    return rc


def disable_timer(logger=None) -> int:
    """Menu option 6: stop and disable the timer (units left in place)."""
    logger = logger or common.get_logger("schedule")
    common.banner(logger, f"STOP {INTERVAL.upper()} UPDATE AUTOMATION")

    if not common.have_command("systemctl"):
        logger.error("systemctl not found -- needs a systemd host (Kali/Debian).")
        return 1

    rc = common.run(["systemctl", "disable", "--now", TIMER_NAME],
                    logger=logger, use_sudo=True)
    if rc == 0:
        logger.info("Stopped and disabled %s.", TIMER_NAME)
    else:
        logger.warning("disable returned rc=%s (timer may not have been set up).", rc)
    return rc


def status_timer(logger=None) -> int:
    """Show whether the timer is active and when it next fires."""
    logger = logger or common.get_logger("schedule")
    if not common.have_command("systemctl"):
        logger.error("systemctl not found.")
        return 1
    return common.run(["systemctl", "list-timers", TIMER_NAME, "--no-pager"],
                      logger=logger, use_sudo=True)


def main() -> int:
    return enable_timer(common.get_logger("schedule"))


if __name__ == "__main__":
    raise SystemExit(main())
