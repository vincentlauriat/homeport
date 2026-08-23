<!-- ARCHIVÉ le 2026-08-23. Cette identité — « The Harbormaster's Desk » — a été
     remplacée par le système éditorial encre & papier décrit dans le DESIGN.md à la
     racine du dépôt. Conservée comme trace de ce qui a été construit jusqu'à la
     v0.5.1 ; ne plus s'en servir comme référence. -->

---
name: Homeport
description: A home server dashboard that reads what your machine already knows — and presents it well.
colors:
  hull-rust: "#b8452f"
  harbor-paper: "#f6f6f4"
  chart-white: "#ffffff"
  rope-line: "#e3e2dd"
  ink: "#1a1a18"
  driftwood: "#6b6a64"
  signal-green: "#2f8a4c"
  signal-amber: "#c8891a"
  signal-red: "#c0392b"
  fog: "#9a9992"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
    fontSize: "clamp(2rem, 6.5vh, 3rem)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
    fontSize: "clamp(2rem, 6vw, 2.9rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    letterSpacing: "-0.02em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    letterSpacing: "0.06em"
  mono:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, monospace"
    fontSize: "0.72rem"
    lineHeight: 1.45
  scale:
    micro-1: "0.6rem"
    micro-2: "0.62rem"
    micro-3: "0.66rem"
    micro-4: "0.68rem"
    micro-5: "0.6875rem"
    micro-6: "0.7rem"
    micro-7: "0.71rem"
    micro-8: "0.72rem"
    micro-9: "0.74rem"
    micro-10: "0.75rem"
    micro-11: "0.76rem"
    dense-1: "0.78rem"
    dense-2: "0.8125rem"
    dense-3: "0.82rem"
    dense-4: "0.85rem"
    body: "0.875rem"
    dense-5: "0.9rem"
    dense-6: "0.9375rem"
    dense-7: "0.95rem"
    metric-1: "1rem"
    metric-2: "1.15rem"
    metric-3: "1.3rem"
    metric-4: "1.4rem"
    metric-5: "1.45rem"
    title: "1.5rem"
    count: "2.2rem"
    wall-caption-max: "1.05rem"
    wall-clock-max: "3.4rem"
rounded:
  bar: "2px"
  tag: "5px"
  xs: "6px"
  sm: "8px"
  tile: "9px"
  md: "12px"
  lg: "16px"
  pill: "999px"
spacing:
  xs: "0.35rem"
  sm: "0.6rem"
  md: "0.85rem"
  lg: "1.5rem"
  xl: "2rem"
components:
  card:
    backgroundColor: "{colors.chart-white}"
    rounded: "{rounded.md}"
    padding: "0.85rem 0.9rem"
  pill:
    backgroundColor: "{colors.chart-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0.3rem 0.7rem"
  chip-up:
    textColor: "{colors.signal-green}"
    rounded: "{rounded.pill}"
    padding: "0.25rem 0.55rem"
  button-action:
    backgroundColor: "{colors.chart-white}"
    textColor: "{colors.hull-rust}"
    rounded: "{rounded.sm}"
    padding: "0.3rem 0.8rem"
  button-action-armed:
    backgroundColor: "{colors.hull-rust}"
    textColor: "{colors.chart-white}"
    rounded: "{rounded.sm}"
    padding: "0.3rem 0.8rem"
  nav-link-current:
    backgroundColor: "{colors.hull-rust}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "0.25rem 0.7rem"
---

# Design System: Homeport

## Overview

**Creative North Star: "The Harbormaster's Desk"**

Homeport looks like the desk of a calm, competent harbormaster: the whole port visible at
a glance, the registers within reach, and nothing spectacular as long as everything is
fine. The interface is a quiet instrument — warm paper neutrals, thin rope-colored rules,
and numbers set in tabular figures — where color is reserved for meaning. The brand accent
(Hull Rust) signs the interface; the three signal colors (green, amber, red) report on the
world. When the port is healthy the page is almost monochrome; a red edge on one card is
an event precisely because nothing else shouts.

The same truth is served in four registers — Classic cards, the dense Control room, the
narrative Journal, the across-the-room Wall — and they share one stylesheet, one token
set, and one state vocabulary. Density changes; the language never does. Both themes are
first-class: a warm paper light theme and a charcoal dark theme, switched by
`prefers-color-scheme` with no manual toggle.

**Key Characteristics:**
- Warm, matte neutrals; color only where it means something.
- State (up / warn / down / unknown) is the system's only loud voice.
- Hairline borders structure the page; shadows only whisper.
- Tabular numerals everywhere a value can change.
- System font stack, self-hosted everything, no external requests.

## Colors

A warm paper-and-ink neutral base, one rust-toned brand accent, and a strict three-color
state vocabulary — every tinted background is derived live via `color-mix`, never a new hex.

### Primary
- **Hull Rust** (#b8452f · dark: #e2705a): the only brand color. Signs the interface —
  the active nav pill, links, progress bars, sparklines, focus accents, action buttons.
  Never used to report a state.

### Neutral
- **Harbor Paper** (#f6f6f4 · dark: #16181a): page background; also the inset background
  of logs, tags, and inputs inside cards.
- **Chart White** (#ffffff · dark: #1e2124): surface of every card, panel, pill, and cell.
- **Rope Line** (#e3e2dd · dark: #2c3034): hairline borders, dividers, dotted key-value
  rules, empty gauge tracks.
- **Ink** (#1a1a18 · dark: #e8e6e1): primary text.
- **Driftwood** (#6b6a64 · dark: #93938c): secondary text — labels, notes, descriptions,
  footers.
- **Fog** (#9a9992 · dark: #6a6a64): the "unknown" state — offline dots, unqualified edges.

### State (functional triad)
- **Signal Green** (#2f8a4c · dark: #4caf6a): up, healthy, online, "all is well".
- **Signal Amber** (#c8891a · dark: #d9a441): warn, degraded, new-device attention.
- **Signal Red** (#c0392b · dark: #e05c4c): down, outage, failure.

### Named Rules
**The State Owns Color Rule.** Within content, color always encodes state. Hull Rust may
sign chrome (nav, links, charts) but never reports health; green/amber/red never decorate.

**The Mixed Tint Rule.** Tinted backgrounds are always derived as
`color-mix(in srgb, var(--state) 10–16%, var(--surface))` and tinted borders as
35–50% mixes into `var(--border)`. No hand-picked pastel hexes, ever — this keeps both
themes correct for free.

## Typography

**Display/Body Font:** system stack (-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif)
**Mono Font:** ui-monospace, "SF Mono", Menlo, monospace

**Character:** the native voice of the machine it runs on — deliberately unbranded,
fast, and legible. Personality comes from restraint: tight negative letter-spacing on big
numbers, wide-tracked uppercase micro-labels, and tabular numerals throughout.

### Hierarchy
- **Display** (700, clamp(2rem, 6.5vh, 3rem), lh 1, -0.02em): the Wall's giant readings
  and clock — sized in viewport-height units to stay readable across the room. Wall
  variants: clamp(2.2rem, 6vh, 3.4rem) for the clock, clamp(1rem, 2.6vh, 1.45rem) and
  clamp(.85rem, 2vh, 1.05rem) for tile values and captions, 2.2rem for big counts.
- **Headline** (700, clamp(2rem, 6vw, 2.9rem), lh 1.1, -0.02em): the Journal's verdict
  ("All is well."), colored by state.
- **Title** (600, 1.5rem, -0.02em): the hostname in the topbar; intermediate numeric
  titles and metric values at 1rem, 1.15rem, 1.3rem, 1.4rem and 1.45rem.
- **Body** (400, 0.875rem base, lh 1.5): default prose; dense views step down through
  0.95, 0.9375, 0.9, 0.85, 0.82, 0.8125 and 0.78rem.
- **Label** (600, 0.6–0.76rem, uppercase, +0.06 to +0.12em): metric labels, group
  headings, tile captions — the denser or larger-format the view, the wider the tracking.
  As-built steps: 0.6, 0.62, 0.66, 0.68, 0.6875, 0.7, 0.71, 0.72, 0.74, 0.75, 0.76rem.
- **Mono** (0.72rem, lh 1.45): container logs, cron commands, MAC addresses, technical tags.

The ramp is deliberately fine-grained: three device classes (wall, phone, desk) and very
dense Operate views each earn quarter-step sizes rather than forcing a coarse scale.

### Named Rules
**The Tabular Numbers Rule.** Any value that can change is set with
`font-variant-numeric: tabular-nums` — counts, percentages, temperatures, uptimes, clocks.
Numbers never jiggle their neighbors.

**The Whisper Label Rule.** Structure is announced in small uppercase Driftwood labels,
never in large headings. The data is the headline; the label is the whisper.

## Layout

Every view is a full-bleed page with fluid padding (`clamp(1rem, 4vw, 3rem)` horizontal)
under a shared topbar (identity ⚓ + hostname, state pills, view-switch nav). Content is
organized in responsive auto-fit grids of cards (`minmax(170–280px, 1fr)`, gaps
0.6–1rem); columns collapse naturally, with single-column fallbacks at 520px.

Density is per-register, not per-token: Classic breathes (0.875rem base), Control
compresses (0.78rem, two columns collapsing at 900px), the Journal centers a 58rem
reading column, and the Wall is a viewport-filling 3-column grid (2 at 820px, 1 at
520px) with `clamp(..., vh, ...)` spacing so it always fills exactly one screen —
`100dvh`, no scroll. Spacing follows a loose rem rhythm (0.35 / 0.6 / 0.85 / 1.5 / 2rem)
rather than a strict scale.

## Elevation & Depth

A hybrid: structure comes from hairline borders (1px Rope Line), not from shadow. Every
card carries the single ambient shadow token (`0 1px 2px rgba(0,0,0,.05), 0 4px 12px
rgba(0,0,0,.04)`; slightly deeper in dark mode) — felt, not seen. Depth inside a card is
conveyed by inset panels (Harbor Paper background + border) for logs, tags, and inputs.
The one glow in the system is the Wall's status halo (`box-shadow: 0 0 22px 4px` at 45%
state color) — an intentional beacon, not an elevation.

### Named Rules
**The Whisper Shadow Rule.** One shadow token for everything; it renders surfaces
slightly lifted off the paper and nothing more. No hover lifts, no layered elevations,
no colored shadows (the Wall halo excepted).

## Shapes

Soft, consistent rounding: 12px (`--radius`) on all cards and panels, 16px on the Wall's
cells, 8px on inner elements (buttons, logs, inputs), 5–6px on the smallest tags, and
full pills (999px) for everything that counts or filters (pills, chips, peers, badges,
nav). Status dots are plain 7–9px circles. The signature silhouette is the **state edge**:
a 3px (4px for attention rows) left border on cards colored by state — the fastest-scanning
element in the whole system.

## Components

### Navigation (view-switch)
- A pill-shaped segmented control listing the views; deliberately frozen rendering
  (0.75rem, no uppercase inheritance) so it looks identical in every context.
- Links: Driftwood → Ink on hover; the current view is a Hull Rust pill with white text.

### Cards (service / metric / health / chart)
- **Corner:** 12px; **Background:** Chart White; **Border:** 1px Rope Line + 3px state
  left edge (service and health cards); **Shadow:** the ambient token.
- Service cards are native `<details>`: header row (emoji icon, name, description, state
  chip, chevron) opens to a detail panel of mini-tables. Down/degraded cards ship
  pre-opened — the reason is visible without a click exactly when it matters.
- Header hover: background shifts to Harbor Paper. No lift, no scale.

### Pills & Chips
- **Summary pills:** white pill, hairline border, bold tabular count colored by state.
- **State chips:** uppercase 0.6875rem, 16% state tint background, state-colored text.
- **Tags:** 0.6875rem Driftwood on Harbor Paper, 5px radius; mono variant for technical
  values.

### Buttons (actions: restart, wake, ack)
- Quiet by default: white surface, 8px radius, hairline border mixed 45–50% with the
  action color, Hull Rust text (green for ack).
- **Armed state:** two-step confirmation — the button fills solid Hull Rust with white
  text. Filling is the confirmation cue.
- **Disabled:** 50% opacity. Results are announced as small colored text, not toasts.

### Inputs / Fields
- White (search) or Harbor Paper (inline edit, textarea) background, hairline border,
  8–12px radius, `font: inherit`. Focus/edit state: border switches to Hull Rust.

### Gauges & Sparklines
- Gauges: 3–4px tracks in Rope Line, Hull Rust fill, animated width (.4s ease).
- Sparklines/charts: 1.5–1.6px Hull Rust stroke over a 12–14% Hull Rust area fill;
  outage bands overlay in 22% Signal Red.

### The Wall Cell (signature)
- 16px radius, viewport-scaled padding, whisper label on top, giant tabular reading
  pinned to the bottom (`margin-top: auto`), colored by state; warn/down cells also tint
  their border. Built to be read from meters away.

## Do's and Don'ts

### Do:
- **Do** derive every tinted background or border with `color-mix` from the state tokens
  (10–16% on surface, 35–50% into borders).
- **Do** keep both themes working through the CSS variables only — no theme-conditional
  rules outside `:root`, values switch by `prefers-color-scheme`.
- **Do** use the state left-edge (3px) as the primary health signal on any new card type.
- **Do** set every mutable number in tabular figures, and keep uppercase micro-labels
  (0.62–0.75rem, +0.06–0.12em) as the only structural captions.
- **Do** use native HTML behavior first (`<details>`, real links, system fonts) — the
  no-framework constraint is part of the design.

### Don't:
- **Don't** introduce new hex values for states or tints — the ten tokens in `:root` are
  the entire palette.
- **Don't** use Hull Rust to express health, or green/amber/red to decorate chrome.
- **Don't** add hover lifts, scale effects, layered shadows, or gradients — motion is
  limited to width/color transitions (0.15–0.4s ease) and the chevron rotation.
- **Don't** load any external resource (fonts, icons, CDNs) — emoji and inline SVG are
  the icon system; anything shipped is served by Homeport.
- **Don't** let the Wall scroll or shrink its readings below across-the-room legibility;
  it must always fill exactly one viewport.
