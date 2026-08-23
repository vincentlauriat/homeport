# Cross-site config backup

Per-host scripts that back up the home-automation config (Home Assistant + Mosquitto,
config only — recorder DBs and logs excluded) to three destinations:

1. a local working history (NVMe), retention 14;
2. a mirror on a distinct physical medium (eMMC/SD), retention 3;
3. an **off-site copy to the other house's Pi** over Tailscale SSH, retention 7 — the two Pis
   back each other up (`raspcorse` ⇄ `raspyellow`).

After a successful off-site copy the script writes a small status JSON (`offsite.json`) that
Homeport reads through a `status_files` tile (`id: offsite`, "Sauvegarde hors-site"), so the
dashboard reflects the real cross-site backup rather than any other mechanism. Contract:
`{"status": "ok"|"error", "message": "…", "last_ts": <unix>}` (see
`homeport/collectors/statusfile.py`).

## Install (per host)

```bash
sudo install -m 0755 deploy/backup/<host>-backup.sh /usr/local/bin/<host>-backup.sh
# then a systemd timer <host>-backup.timer (daily ~03:30, Persistent=true) runs it as root
```

The off-site status path differs by host, matching each Homeport's data dir:
- `raspcorse` → `/mnt/ssd/homeport-data/offsite.json` (systemd drop-in: `User=vincent`, SSD data dir)
- `raspyellow` → `/var/lib/homeport/offsite.json` (`User=homeport`)

Both are overridable via the `OFFSITE_STATUS_FILE` environment variable.

> These run on the Pis, not from this repo. This directory is the source of truth for their
> content; edit here and re-install with the command above.
