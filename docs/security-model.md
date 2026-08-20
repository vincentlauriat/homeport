# Security model

Homeport assumes it is reachable **only** from your LAN and your Tailscale network. Do not
expose it to the Internet — it has no login page, by design.

## Read-only by default

Every page and API endpoint is read-only for everyone on the LAN. The only write endpoints
are device metadata (naming LAN devices) and the two actions below.

## Actions require proof of identity

`POST /api/actions/restart/{service}` and `/api/actions/wake/{mac}` are authorized only when
**both** hold:

1. the client IP belongs to the Tailscale range (100.64.0.0/10) — checked before anything else;
2. `tailscale whois <ip>` maps that IP to the exact login declared as `actions.admin`.

No admin declared (`admin: ~`, the default) → all actions disabled.

## Restarts never touch the Docker socket

Homeport reaches Docker **read-only** through
[tecnativa/docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy) bound to
127.0.0.1 (`CONTAINERS=1`, everything else off). Restarts go through sudo rules that
whitelist exact commands (`docker restart homeassistant` — no wildcards, no shell). A
compromised Homeport process can therefore restart your declared services, and nothing else.

## Outbound traffic

One call: the public IP check (`api.ipify.org`, hourly). Set `intervals: {public_ip: 0}` to
remove it. No telemetry, no update checks, no CDN — all assets are served locally.

## Reporting

See [SECURITY.md](../SECURITY.md).
