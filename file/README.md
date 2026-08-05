# secauto — Kali Update & Security Automation

A small two-layer toolkit:

- **C base (`security.c`)** — an interactive menu/launcher.
- **Python backend (`automation/`)** — does the real work: update, scan, logs.
- **Scheduling (`systemd/`)** — makes updates run *automatically*.

```
kali-update-automation/
├── security.c                # C launcher (the menu)
├── Makefile                  # build + install
├── setup.sh                  # ONE-TIME SETUP (run this first!)
├── automation/
│   ├── secauto.py            # dispatcher (update | scan | logs | all)
│   ├── common.py             # logging, sudo handling, subprocess runner
│   ├── update.py             # apt update/full-upgrade/autoremove/autoclean
│   ├── scan.py               # read-only local security audit
│   └── logs.py               # list / tail / prune logs
└── systemd/
    ├── secauto-update.service
    └── secauto-update.timer
```

## Quick Start (Passwordless Automation)

**Run this once on your Kali machine:**

```bash
cd kali-update-automation
sudo bash setup.sh
```

That's it! The setup script:
1. Installs secauto to `/opt/secauto`
2. Configures passwordless sudo for apt commands
3. Enables the systemd timer (updates every 7 hours)

After setup, everything runs automatically — no password prompts.

## Architecture

The C program never runs apt itself. It resolves its own location via
`/proc/self/exe`, finds `automation/secauto.py` next to it, and runs
`python3 automation/secauto.py <action>`. All policy/logic lives in Python,
which is easier to extend than C.

## Build & run

```bash
cd kali-update-automation
make                 # builds ./secauto
./secauto            # interactive menu
```

You can also drive the backend directly (no C needed):

```bash
python3 automation/secauto.py update
python3 automation/secauto.py scan --deep
python3 automation/secauto.py logs tail --lines 60
python3 automation/secauto.py all
python3 automation/secauto.py schedule-enable    # menu option 5: every 7h
python3 automation/secauto.py schedule-stop      # menu option 6: stop it
python3 automation/secauto.py schedule-status    # menu option 7: next run
```

The interactive menu mirrors these:

```
  1) Update automation    (apt update/upgrade)
  2) Security scan         (local audit)
  3) View logs
  4) Run all               (update + scan)
  5) Enable 7-hour update automation
  6) Stop  7-hour update automation
  7) Schedule status       (next run)
  0) Exit
```

Options 5/6 generate and install the systemd units automatically (pointing
`ExecStart` at wherever `secauto.py` lives), so you do **not** need the manual
`cp systemd/...` step below unless you prefer it. They need root — launch with
`sudo ./secauto` or authenticate when prompted.

### Install system-wide (optional)

```bash
sudo make install                 # -> /opt/secauto/
/opt/secauto/secauto
```

## Privileges

`update` (and parts of `scan`) need root. The Python `run()` helper
auto-prepends `sudo` when you are not root, so you can launch `./secauto` as a
normal user and authenticate when prompted — or run the whole thing under
`sudo` for an unattended run.

## Make updates automatic (the "automation" part)

### Option A — systemd timer (recommended)

```bash
sudo make install
sudo cp systemd/secauto-update.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now secauto-update.timer
systemctl list-timers secauto-update.timer     # confirm next run
```

The shipped timer runs the update **every 7 hours** (`OnUnitActiveSec=7h`,
first run 10 min after boot). To change the interval, edit `OnUnitActiveSec`
in `secauto-update.timer` (e.g. `12h`, `30min`) and re-run the `cp` +
`daemon-reload` above.

### Option B — cron

cron has no native "every 7 hours" syntax (`*/7` resets at midnight, leaving a
short final gap). Either accept that approximation, or compute hours from the
Unix epoch so the spacing stays exact:

```bash
sudo crontab -e
# Approximate: at minute 0 of hours 0,7,14,21 (gap before midnight is <7h)
0 0,7,14,21 * * * /usr/bin/python3 /opt/secauto/automation/secauto.py update >> /var/log/secauto/cron.log 2>&1

# Exact 7h spacing: run hourly but only act when epoch-hours % 7 == 0
0 * * * * [ $(( $(date +\%s) / 3600 \% 7 )) -eq 0 ] && /usr/bin/python3 /opt/secauto/automation/secauto.py update >> /var/log/secauto/cron.log 2>&1
```

The systemd timer (Option A) is the cleaner way to get a true 7-hour interval.

## Logs

Written to `/var/log/secauto/` when run as root, otherwise
`~/.local/share/secauto/logs/`. Files rotate at ~1 MB (5 backups).

```bash
python3 automation/secauto.py logs list
python3 automation/secauto.py logs tail --name update.log
```

## Safety notes

- `scan` is **read-only** and **local-only** — it audits *this* host
  (pending updates, listening sockets, failed services, changed package
  files). It does not touch other machines.
- `update` keeps your existing config files on conffile conflicts
  (`--force-confold`) so unattended runs never hang on a prompt. Review
  `/var/log/secauto/update.log` periodically for `.dpkg-dist` notices.

## What was fixed from the original C snippet

The starter snippet had a few issues — corrected here:

| Original | Problem | Fix |
|----------|---------|-----|
| `int main {` | missing `()` | `int main(void) {` |
| `int automate = 3` | missing `;` | added `;` (now read from user input) |
| `printf("...\/n")` | `/n` is not a newline | `\n` |
| `voil security` | typo / not valid C | removed; logic moved to functions |
| `return 1;` | non-zero = failure | `return 0;` on clean exit |

Plus: a real input loop, safe input parsing (`fgets`+`strtol`), and dispatch
to the Python backend instead of just printing labels.
