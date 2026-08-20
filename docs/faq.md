# FAQ

**Why isn't there an official Docker image?**
Homeport supervises the *host*: systemd units, `/sys` sensors, `ip neigh`, the journal.
Containerizing it means punching so many holes in the sandbox that the container adds risk
rather than isolation. It runs as an unprivileged systemd service instead.

**How is this different from Uptime Kuma?**
Uptime Kuma asks "does it answer?". Homeport also asks Docker and systemd, and flags the
disagreements (a running container whose app is dead). It also covers the machine itself
(temperatures, SSD wear, power, updates) and the LAN around it.

**And from Grafana + Prometheus?**
That stack is wonderful — and heavy. Homeport is one service, one SQLite file, zero agents,
made for a single home server you want to glance at, not query.

**Does it work outside Raspberry Pi?**
Yes — any Debian-like with systemd. Pi-specific tiles (throttling, fan, EEPROM) appear only
when the hardware exposes them.

**How do updates work?**
`sudo ./deploy/update.sh` on the server (git fast-forward + idempotent reinstall). The
footer shows a badge when a newer release exists — a daily check against GitHub Releases
you can turn off.

**Where is my data?**
`/var/lib/homeport/history.db` (SQLite). Seven days of samples by default. Nothing leaves
your machine.
