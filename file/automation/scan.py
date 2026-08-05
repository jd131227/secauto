#!/usr/bin/env python3
"""Security scan: a READ-ONLY local audit of this host.

Nothing here modifies the system or touches other machines -- it only reports
on the local box's update/security hygiene. Optional auditing tools
(lynis, rkhunter, debsums) are used only when already installed.
"""
from __future__ import annotations

import common


def _section(logger, title, cmd, use_sudo=False):
    """Print a titled section, running `cmd` if its binary exists."""
    logger.info("")
    logger.info("--- %s ---", title)
    if not common.have_command(cmd[0]):
        logger.info("(skipped: %s not installed)", cmd[0])
        return None
    return common.run(cmd, logger=logger, use_sudo=use_sudo)


def run_scan(logger=None, deep=False) -> int:
    logger = logger or common.get_logger("scan")
    common.banner(logger, "LOCAL SECURITY SCAN (read-only)")

    # Pending package upgrades (simulation; no root needed).
    _section(logger, "Pending package upgrades",
             ["apt-get", "-s", "upgrade"])

    # Open / listening sockets (root reveals owning process via -p).
    if common.have_command("ss"):
        _section(logger, "Listening sockets", ["ss", "-tulnp"], use_sudo=True)
    else:
        _section(logger, "Listening sockets", ["netstat", "-tulnp"], use_sudo=True)

    # Failed systemd services.
    _section(logger, "Failed services",
             ["systemctl", "--failed", "--no-pager"])

    # Disk usage and who is logged in.
    _section(logger, "Disk usage", ["df", "-h"])
    _section(logger, "Logged-in users", ["who"])

    # Verify installed package files have not been altered.
    _section(logger, "Changed package files (debsums)",
             ["debsums", "-s"], use_sudo=True)

    # Heavier audits only on --deep and only if the tool is present.
    if deep:
        _section(logger, "Lynis system audit",
                 ["lynis", "audit", "system", "--quick"], use_sudo=True)
        _section(logger, "rkhunter check",
                 ["rkhunter", "--check", "--sk", "--nocolors"], use_sudo=True)

    logger.info("")
    logger.info("Scan complete. Review the log for full details.")
    return 0


def main() -> int:
    return run_scan(common.get_logger("scan"), deep=False)


if __name__ == "__main__":
    raise SystemExit(main())
