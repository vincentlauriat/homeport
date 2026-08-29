# Getting started — macOS

This installs a **second, reduced instance** next to your Pi(s) — not a replacement, and
not a full instance. See [what's out of scope](#out-of-scope-by-design) below.

## Requirements

- macOS (Apple Silicon or Intel), Python 3.11+
- Optional: [Homebrew](https://brew.sh) (outdated-package check)

## Install

```bash
git clone https://github.com/vincentlauriat/homeport && cd homeport
./deploy/macos/install.sh
# open http://localhost:8080 — no sudo needed to run this line
```

The installer copies the app and creates a venv under `~/Library/Application
Support/Homeport/app`, the example config under `.../config` (never overwriting yours),
and loads two `launchd` jobs:

- **`com.vincentlauriat.homeport`** — the dashboard itself, as a `LaunchAgent` under your
  own user, no privilege. Port `8080` by default (a `LaunchAgent` can't bind a privileged
  port anyway) — override with `HOMEPORT_PORT=<port> ./deploy/macos/install.sh`.
- **`com.vincentlauriat.homeport.thermal`** — a small root `LaunchDaemon`, installed with
  `sudo`, that reads thermal pressure every 60 s. `powermetrics` requires root; the
  dashboard itself never does. Nothing else on this machine needs `sudo`.

Re-run `./deploy/macos/install.sh` after every `git pull` to update both jobs.

## Configure

Same file format as the Linux install: `~/Library/Application Support/Homeport/config/
services.yaml`, re-read on every request. Full reference:
[configuration.md](configuration.md).

## What it watches on macOS

CPU load, memory, disk, macOS software updates (`softwareupdate`), Homebrew outdated
packages, and thermal pressure (Apple's qualitative scale — nominal/moderate/heavy/
trapping/sleeping — since current `powermetrics` no longer reports a CPU temperature in
°C or a fan speed the way it did on older Macs).

## Out of scope, by design

Docker and supervised services (no `systemd` equivalent is wired in), LAN device scanning
and Wake-on-LAN, Tailscale peers, Starlink/Livebox — a Mac on the same network as your Pi
would just duplicate what the Pi already watches. If you want a full instance, run
Homeport on Linux instead.

## Demo mode

Same as Linux: `HOMEPORT_DEMO=1 venv/bin/uvicorn homeport.main:app --port 8080` renders
the full dashboard, macOS tiles included, on simulated data — no system access.
