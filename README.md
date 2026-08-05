# secauto — Kali Update & Security Automation

A small two-layer toolkit that automates routine Kali Linux maintenance: system updates, a local security audit, and log management, with optional scheduled execution via systemd.

## Architecture

## Architecture

- `security.c` — C launcher (the menu)
- `secauto`
- `Makefile` — build + install
- `setup.sh`
- `README.md`
- `automation/`
  - `secauto.py` — dispatcher (update | scan | logs | all)
  - `common.py` — logging, sudo handling, subprocess runner
  - `update.py` — apt update/full-upgrade/autoremove/autoclean
  - `scan.py` — read-only local security audit
  - `logs.py` — list / tail / prune logs
- `systemd/`
  - `secauto-update.service`
  - `secauto-update.timer`

The C program is a thin launcher — it never runs `apt` itself. It resolves its own location via `/proc/self/exe`, finds `automation/secauto.py` next to it, and dispatches to Python, which owns all the actual policy and logic (easier to extend and test than doing it in C).

## Features

- **Update automation** — `apt update` / `full-upgrade` / `autoremove` / `autoclean` in one command
- **Local security scan** — a read-only local security audit
- **Log management** — list, tail, and prune automation logs
- **Scheduling** — enable/disable a recurring update cycle via systemd timers, generated and installed automatically
- **Interactive menu** — a simple numbered menu for anyone who prefers not to remember flags

## Build & Run

```bash
cd kali-update-automation
make                 # builds ./secauto
./secauto            # interactive menu
```

Or drive the backend directly, no C build required:

```bash
python3 automation/secauto.py update
python3 automation/secauto.py scan --deep
python3 automation/secauto.py logs tail --lines 60
python3 automation/secauto.py all
python3 automation/secauto.py schedule-enable    # every 7 hours
python3 automation/secauto.py schedule-stop
python3 automation/secauto.py schedule-status
```

Interactive menu:
1. Update automation (apt update/upgrade)
2. Security scan (local audit)
3. View logs
4. Run all (update + scan)
5. Enable 7-hour update automation
6. Stop 7-hour update automation
7. Schedule status (next run)
8. Exit

### Install system-wide (optional)

```bash
sudo make install                 # -> /opt/secauto/
/opt/secauto/secauto
```

## Privileges

`update` (and parts of `scan`) require root. The Python `run()` helper auto-prepends `sudo` when not already running as root, so you can launch `./secauto` as a normal user and authenticate when prompted.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

Yuto Sugihara — Security Engineer specializing in enterprise cybersecurity operations, SIEM tooling, and IT infrastructure automation.



