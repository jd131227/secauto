#!/usr/bin/env python3
"""Update automation: refresh, upgrade, and clean APT packages on Kali/Debian.

Runs the full unattended-upgrade sequence:
    apt-get update
    apt-get full-upgrade   (config-file prompts answered automatically)
    apt-get autoremove
    apt-get autoclean
"""
from __future__ import annotations

import common

# Prefix that survives `sudo` (sudo's env_reset would drop a Python env= dict).
# `env VAR=...` is executed by sudo and sets the variable for apt-get.
_NONINTERACTIVE = ["env", "DEBIAN_FRONTEND=noninteractive"]

# Keep existing config files on conffile conflicts instead of hanging on a
# prompt -- the standard choice for unattended upgrades.
_DPKG_KEEP_CONF = [
    "-o", "Dpkg::Options::=--force-confdef",
    "-o", "Dpkg::Options::=--force-confold",
]


def run_update(logger=None, full=True, autoremove=True, clean=True) -> int:
    logger = logger or common.get_logger("update")
    common.banner(logger, "APT UPDATE AUTOMATION")

    if not common.have_command("apt-get"):
        logger.error("apt-get not found -- this tool targets Debian/Kali.")
        return 1

    steps = [
        _NONINTERACTIVE + ["apt-get", "update"],
    ]
    upgrade_cmd = "full-upgrade" if full else "upgrade"
    steps.append(
        _NONINTERACTIVE + ["apt-get", "-y", *_DPKG_KEEP_CONF, upgrade_cmd]
    )
    if autoremove:
        steps.append(_NONINTERACTIVE + ["apt-get", "-y", "autoremove"])
    if clean:
        steps.append(_NONINTERACTIVE + ["apt-get", "-y", "autoclean"])

    failures = 0
    for step in steps:
        rc = common.run(step, logger=logger, use_sudo=True)
        if rc != 0:
            failures += 1
            logger.warning("Step failed (continuing): %s", " ".join(step))

    if failures:
        logger.warning("Update completed with %d failed step(s).", failures)
        return 1
    logger.info("Update completed successfully.")
    return 0


def main() -> int:
    return run_update(common.get_logger("update"))


if __name__ == "__main__":
    raise SystemExit(main())
