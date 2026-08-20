# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, on equal footing (confirmed): Vincent's own household homeserver defines the
features, but every screen must remain understandable by a stranger who installs Homeport
from GitHub. Primary user is the self-hosting admin of a home server (Raspberry Pi or small
Debian box) who wants to know "is everything fine?" at a glance and act (restart, wake)
when it is not. Secondary readers include non-admin household members glancing at the wall
display.

Confirmed usage screens, all three first-class:
- **Wall tablet** — the Mur view runs permanently, read from across the room, PWA fullscreen.
- **Phone over Tailscale** — quick checks and actions on the go, narrow screens.
- **Desktop / laptop** — seated admin sessions: Contrôle, Historique, diagnostics.

## Product Purpose

Homeport supervises a self-hosted home server: services (Docker, systemd, own TCP/HTTP
probes), machine health (CPU, memory, temperatures, SSD wear, Pi under-voltage), local
network (device inventory, Tailscale, Internet health, Starlink), and history (7 days of
charts, outage bands, availability percentages). An authenticated admin can restart
services and wake machines. Success is a truthful, immediate answer to "is everything
fine?" — and a safe path to fix it when not.

## Positioning

Deliberately between "too simple" (a probe list) and "too heavy" (a metrics stack): no
agents, no external database, no JavaScript framework. One Python service, one SQLite
file, one YAML config. Its distinctive mechanism is cross-checking up to three sources of
truth per service (Docker state, systemd state, its own probe) and surfacing *degraded*
states that `docker ps` hides.

## Operating Context

- Runs on the LAN of a home network; often consulted from outside via Tailscale.
- Seven server-rendered views sharing one nav: Classic (index), Contrôle, Journal, Mur,
  Réseau, Starlink, Historique.
- LAN access is strictly read-only; actions require Tailscale + `tailscale whois` mapping
  to the single declared admin. Restarts go through exact-command sudoers, Docker is
  reached read-only via a socket proxy.
- Demo mode (`HOMEPORT_DEMO=1`) renders the full dashboard on simulated data — the
  standard way to run and inspect the UI without a real server.
- Everything degrades gracefully: no Docker, no Tailscale, no Raspberry Pi → the related
  tiles simply disappear. The UI must never present a missing integration as an error.

## Capabilities and Constraints

- Stack: FastAPI + Jinja2 server-rendered templates, vanilla JS per view, one shared
  `style.css`. No JS framework — a durable product commitment, not a gap.
- **Offline/self-hosted (confirmed):** no CDN, no external requests from pages. Fonts may
  be embedded in the repo (woff2 served by Homeport itself); system-font stacks are the
  current baseline. The service makes exactly one outbound call (public IP), disableable.
- i18n: English default, French included; all UI strings live in `homeport/i18n/*.json`.
  New UI copy must go through these files, both languages.
- PWA: installable, `manifest.json` present, theme color `#b8452f`.
- Light and dark themes via `prefers-color-scheme`.
- No telemetry. MIT license.

## Brand Commitments

- Name **Homeport** with the ⚓ anchor mark and light nautical vocabulary (port, journal,
  mur…) — established identity, not to be replaced casually.
- Tone of the Journal view: calm, narrative, human ("All is well.").

## Evidence on Hand

- Real screenshots of the four main views in `docs/screenshots/` (used by README).
- Demo mode generates realistic data for any screen — no need to fabricate content.
- No testimonials, benchmarks, or customer claims exist; none may be invented.

## Product Principles

1. **Truth over reassurance** — the dashboard reports what the machine actually knows,
   including disagreements between sources; never paint a degraded state green.
2. **Glanceable first, drill-down second** — every view answers "is everything fine?"
   before it explains anything.
3. **Self-contained by design** — no agents, frameworks, CDNs, or external dependencies;
   anything shipped must be served by Homeport itself.
4. **Graceful absence** — missing integrations disappear silently; the UI never nags
   about what isn't installed.
5. **Same truth, four registers** — Classic, Contrôle, Journal and Mur are different
   readings of one dataset, not different products; changes must keep them coherent.

## Accessibility & Inclusion

Wall view must stay readable from across a room (large numerals, high contrast in both
themes). No other product-specific standard has been established.
