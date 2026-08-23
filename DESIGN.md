---
name: Homeport
description: "Un cadre éditorial noir-et-blanc, calme et sûr de lui, ponctué de blocs pastel narratifs — un tableau de bord qui dit la vérité en encre sur papier, et garde les couleurs saturées pour les seuls signaux d'état."
status: final
updated: 2026-08-23

colors:
  # ----- Cœur monochrome (repris de l'import DESIGN-figma) -----
  ink: '#000000'
  canvas: '#ffffff'
  inverse-canvas: '#000000'
  inverse-ink: '#ffffff'
  surface-soft: '#f7f7f5'
  hairline: '#cfcfcb'
  hairline-soft: '#e6e6e4'
  # Rôle secondaire de texte — écart assumé vis-à-vis de l'import (voir Colors). [ASSUMPTION]
  ink-soft: '#5c5c57'
  # ----- Blocs pastel narratifs (hex de l'import, approximations fidèles) -----
  block-lime: '#dceeb1'
  block-lilac: '#c5b0f4'
  block-cream: '#f4ecd6'
  block-pink: '#efd4d4'
  block-mint: '#c8e6cd'
  block-coral: '#f3c9b6'
  block-navy: '#1f1d3d'
  accent-magenta: '#ff3d8b'
  overlay-scrim: '#000000'
  # ----- Triade sémantique d'état (hors palette pastel — décision memlog) -----
  state-up: '#1ea64a'
  state-warn: '#c07f00'      # 3.35:1 sur le canevas — mesuré, pas supposé
  state-down: '#d92d20'      # [ASSUMPTION]
  state-unknown: '#8a8a85'   # [ASSUMPTION]
  # Variantes texte assises vers l'encre pour tenir AA en petit corps. [ASSUMPTION]
  state-up-text: '#15733a'
  state-warn-text: '#8a6410'
  state-down-text: '#b3271e'
  # ----- Palette sombre dérivée (encre inversée, pastels assombris) — tout [ASSUMPTION] -----
  canvas-dark: '#121211'
  ink-dark: '#f4f3f0'
  ink-soft-dark: '#a3a29b'
  surface-soft-dark: '#1c1c1a'
  hairline-dark: '#3a3a37'
  hairline-soft-dark: '#2b2b29'
  block-lime-dark: '#39411f'
  block-lilac-dark: '#352a52'
  block-cream-dark: '#3b3527'
  block-pink-dark: '#442e2e'
  block-mint-dark: '#25392a'
  block-coral-dark: '#46311f'
  block-navy-dark: '#1f1d3d'
  state-up-dark: '#4cc272'
  state-warn-dark: '#dcab4a'
  state-down-dark: '#ef6a5c'
  state-unknown-dark: '#6f6f68'
  state-up-text-dark: '#63cd84'
  state-warn-text-dark: '#e0b660'
  state-down-text-dark: '#f28376'

typography:
  # Inter variable (sans) + JetBrains Mono (mono), woff2 embarquées — jamais de CDN.
  # Graisses fines de l'import (320/330/340/480/540/700) conservées telles quelles sur
  # l'axe wght continu d'Inter variable.
  display-xl:            # Hero de la landing GitHub Pages. Recalibré 86→72. [ASSUMPTION]
    fontFamily: Inter
    fontSize: 72px
    fontWeight: 340
    lineHeight: 1.02
    letterSpacing: -1.44px
  display-lg:            # Ouvertures de section (landing). [ASSUMPTION]
    fontFamily: Inter
    fontSize: 52px
    fontWeight: 340
    lineHeight: 1.08
    letterSpacing: -0.78px
  display:               # Verdict du Journal, état du Mur. [ASSUMPTION]
    fontFamily: Inter
    fontSize: 40px
    fontWeight: 540
    lineHeight: 1.1
    letterSpacing: -0.8px
  headline:              # Titres de panneaux et de blocs narratifs. [ASSUMPTION]
    fontFamily: Inter
    fontSize: 22px
    fontWeight: 540
    lineHeight: 1.35
    letterSpacing: -0.22px
  title:                 # Titres de cartes de service. [ASSUMPTION]
    fontFamily: Inter
    fontSize: 15px
    fontWeight: 540
    lineHeight: 1.4
    letterSpacing: -0.1px
  body-lg:               # Corps de la landing, récit du Journal. [ASSUMPTION]
    fontFamily: Inter
    fontSize: 17px
    fontWeight: 330
    lineHeight: 1.5
    letterSpacing: -0.12px
  body:                  # Corps par défaut de l'app (dense). [ASSUMPTION]
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 340
    lineHeight: 1.5
    letterSpacing: -0.08px
  body-sm:               # Descriptions, notes de tuiles, méta. [ASSUMPTION]
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 340
    lineHeight: 1.45
    letterSpacing: 0
  link:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 480
    lineHeight: 1.4
    letterSpacing: -0.06px
  button:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 480
    lineHeight: 1.4
    letterSpacing: -0.06px
  eyebrow:               # Étiquettes de section, mono capitales, tracking positif.
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: 0.66px
  caption:               # Pied de page, horodatages, colonnes.
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: 0.6px
  data-xl:               # Grands chiffres du Mur, horloge. tabular-nums. [ASSUMPTION]
    fontFamily: Inter
    fontSize: 48px
    fontWeight: 540
    lineHeight: 1.0
    letterSpacing: -0.96px
  data-md:               # Valeurs de métriques (CPU %, températures). tabular-nums. [ASSUMPTION]
    fontFamily: Inter
    fontSize: 22px
    fontWeight: 540
    lineHeight: 1.1
    letterSpacing: -0.22px
  data-sm:               # Valeurs en ligne dans les tables. tabular-nums. [ASSUMPTION]
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 480
    lineHeight: 1.4
    letterSpacing: 0

rounded:
  xs: 2px
  sm: 6px
  md: 8px
  lg: 24px
  xl: 32px
  pill: 50px
  full: 9999px

spacing:
  hair: 1px
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 96px

components:
  top-nav:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body-sm}'
    height: 56px
  view-switch-tab-default:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink-soft}'
    typography: '{typography.button}'
    rounded: '{rounded.pill}'
    padding: 4px 12px
  view-switch-tab-selected:
    backgroundColor: '{colors.ink}'
    textColor: '{colors.canvas}'
    typography: '{typography.button}'
    rounded: '{rounded.pill}'
    padding: 4px 12px
  status-pill:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body-sm}'
    rounded: '{rounded.pill}'
    border: '1px {colors.hairline}'
    padding: 4px 12px
  state-chip:
    backgroundColor: '{colors.surface-soft}'
    textColor: '{colors.state-up-text}'
    typography: '{typography.eyebrow}'
    rounded: '{rounded.pill}'
    padding: 3px 9px
  state-dot:
    backgroundColor: '{colors.state-up}'
    rounded: '{rounded.full}'
    size: 8px
  service-card:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body-sm}'
    rounded: '{rounded.md}'
    border: '1px {colors.hairline}'
    stateRail: '3px {colors.state-up}'
    padding: 14px 16px
  service-row:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.data-sm}'
    borderBottom: '1px {colors.hairline-soft}'
    padding: 6px 8px
  metric-tile:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.data-md}'
    rounded: '{rounded.md}'
    border: '1px {colors.hairline}'
    padding: 14px 16px
  health-tile:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body-sm}'
    rounded: '{rounded.md}'
    border: '1px {colors.hairline}'
    stateRail: '3px {colors.state-up}'
    padding: 14px 16px
  chart-card:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.eyebrow}'
    rounded: '{rounded.md}'
    border: '1px {colors.hairline}'
    strokeColor: '{colors.ink}'
    padding: 14px 16px
  wall-cell:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.data-xl}'
    rounded: '{rounded.lg}'
    border: '1px {colors.hairline}'
    padding: 20px 24px
  verdict:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.display}'
  story-block:
    backgroundColor: '{colors.block-cream}'
    textColor: '{colors.ink}'
    typography: '{typography.body-lg}'
    rounded: '{rounded.lg}'
    padding: 24px 32px
  filter-pill-default:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink-soft}'
    typography: '{typography.body-sm}'
    rounded: '{rounded.pill}'
    border: '1px {colors.hairline}'
    padding: 4px 12px
  filter-pill-selected:
    backgroundColor: '{colors.ink}'
    textColor: '{colors.canvas}'
    typography: '{typography.body-sm}'
    rounded: '{rounded.pill}'
    padding: 4px 12px
  button-primary:
    backgroundColor: '{colors.ink}'
    textColor: '{colors.canvas}'
    typography: '{typography.button}'
    rounded: '{rounded.pill}'
    padding: 8px 16px
  button-secondary:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.button}'
    rounded: '{rounded.pill}'
    border: '1px {colors.hairline}'
    padding: 7px 15px
  button-danger-armed:
    backgroundColor: '{colors.state-down}'
    textColor: '{colors.canvas}'
    typography: '{typography.button}'
    rounded: '{rounded.pill}'
    padding: 8px 16px
  text-input:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body}'
    rounded: '{rounded.md}'
    border: '1px {colors.hairline}'
    padding: 10px 12px
  select-pref:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink-soft}'
    typography: '{typography.caption}'
    rounded: '{rounded.pill}'
    border: '1px {colors.hairline}'
    padding: 3px 9px
  alert-banner:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.body-sm}'
    rounded: '{rounded.md}'
    border: '1px {colors.hairline}'
    stateRail: '3px {colors.state-down}'
    padding: 12px 16px
  tag-mono:
    backgroundColor: '{colors.surface-soft}'
    textColor: '{colors.ink-soft}'
    typography: '{typography.caption}'
    rounded: '{rounded.sm}'
    padding: 2px 7px
  logs-pre:
    backgroundColor: '{colors.surface-soft}'
    textColor: '{colors.ink}'
    typography: '{typography.caption}'
    rounded: '{rounded.md}'
    border: '1px {colors.hairline}'
    padding: 10px 12px
  update-chip:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.caption}'
    rounded: '{rounded.pill}'
    border: '1px {colors.hairline}'
    padding: 2px 10px
  footer:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink-soft}'
    typography: '{typography.caption}'
    borderTop: '1px {colors.hairline}'
    padding: 16px 0
  landing-hero:
    backgroundColor: '{colors.canvas}'
    textColor: '{colors.ink}'
    typography: '{typography.display-xl}'
    padding: 96px 32px
  color-block-section:
    backgroundColor: '{colors.block-lime}'
    textColor: '{colors.ink}'
    typography: '{typography.body-lg}'
    rounded: '{rounded.lg}'
    padding: 48px
---

## Brand & Style

Homeport parle comme un instrument de bord : en encre noire sur papier blanc, avec la
confiance tranquille d'un système qui dit la vérité. L'identité descend directement du
système éditorial importé (`imports/DESIGN-figma.md`) : un cadre rigoureusement monochrome
— chrome, typographie, CTA en pilules — interrompu par des blocs pastel qui portent le
récit, jamais l'état. Sur la landing GitHub Pages, ces blocs prennent la pleine largeur
comme des posters ; dans l'app, ils se font rares et petits — un bloc crème pour le récit
du Journal, un bloc lime pour un livre de bord vierge — parce qu'un tableau de bord dense
n'est pas une page marketing. [ASSUMPTION sur ce dosage app.]

La règle structurante, héritée du memlog : **le pastel raconte, le saturé signale.** Les
blocs `{colors.block-*}` sont narratifs et ne codent jamais un état. Les états up/warn/down
vivent dans une triade sémantique dédiée (`{colors.state-up}`, `{colors.state-warn}`,
`{colors.state-down}`), volontairement hors de la palette pastel — des signaux, pas des
décors. Le nom Homeport, l'ancre ⚓ et le vocabulaire nautique léger (port, journal, mur)
sont conservés tels quels (engagement de marque, PRODUCT.md).

Deux registres, une seule voix : la landing s'autorise l'échelle display et le rythme de
section de 96px de l'import ; l'app recalibre tout vers la densité (corps 14px, tuiles
serrées) sans changer de langage — mêmes pilules, mêmes hairlines, même mono-taxonomie.

## Colors

**Encre et papier.** `{colors.ink}` porte chaque titre, chaque valeur, chaque CTA primaire.
`{colors.canvas}` est le papier ; `{colors.surface-soft}` le seul fond intermédiaire
(tuiles d'illustration, logs, tags). Les séparations se font au hairline —
`{colors.hairline}` pour les bordures de cartes et d'inputs, `{colors.hairline-soft}` pour
les filets de lignes de table — jamais à l'ombre portée.

**`{colors.ink-soft}` — l'écart assumé.** L'import interdit le gris moyen (« weight, not
opacity, carries hierarchy »). Un dashboard dense a pourtant besoin d'un second registre de
texte : notes de tuiles, descriptions de services, horodatages. On garde donc un unique
rôle `ink-soft`, réservé au texte auxiliaire jamais porteur d'information d'état, et la
hiérarchie du texte principal continue de passer par la graisse. [ASSUMPTION — adaptation
documentée dans reconcile-design-figma.md.]

**Blocs pastel.** Les sept surfaces `{colors.block-*}` de l'import sont reprises à
l'identique. Usage : sections de la landing (une par section, pleine largeur), et dans
l'app uniquement des surfaces narratives (`story-block`, états vides). Interdit : associer
une couleur de bloc à un état système (pas de « lime = tout va bien »). `{colors.block-navy}`
reste la seule surface sombre au-dessus du pied de page en thème clair.

**Triade d'état.** `{colors.state-up}` reprend le `semantic-success` de l'import ;
`{colors.state-warn}` et `{colors.state-down}` sont proposés dans le même registre saturé
[ASSUMPTION]. `{colors.state-unknown}` couvre l'absence de mesure [ASSUMPTION]. En petit
corps, on utilise les variantes `{colors.state-up-text}` / `{colors.state-warn-text}` /
`{colors.state-down-text}`, assises vers l'encre pour tenir le contraste AA — le motif
existe déjà dans l'app actuelle et il est conservé. Les tokens pleins restent pour les
dots, rails et fonds teintés.

**`{colors.accent-magenta}`** est conservé comme couleur à usage unique (« single-shot »), réservé à la landing
(un CTA promotionnel par page, maximum). Il n'apparaît nulle part dans l'app.

**Palette sombre.** Dérivée en miroir : l'encre s'inverse (`{colors.canvas-dark}` proche
du noir papier, `{colors.ink-dark}` blanc cassé), les hairlines s'assombrissent, les
pastels deviennent des versions profondes et désaturées de la même teinte
(`{colors.block-lime-dark}`, etc.) pour garder l'esprit sticky-note sans éblouir un mur la
nuit. Les états s'éclaircissent légèrement (`{colors.state-up-dark}`, …) pour rester
lisibles sur fond sombre. Chaque valeur sombre est une dérivation [ASSUMPTION], à arbitrer
au Finalize — l'import ne documente aucun dark mode.

## Typography

**Familles.** **Inter** (variable) remplace figmaSans, **JetBrains Mono** remplace
figmaMono — ce sont les substituts recommandés par l'import lui-même. Les deux sont
embarquées en woff2 servies par Homeport : offline strict, jamais de CDN (PRODUCT.md).
Fallbacks : `Inter, system-ui, -apple-system, sans-serif` et `"JetBrains Mono",
ui-monospace, "SF Mono", Menlo, monospace`. L'axe wght continu d'Inter variable permet de
conserver les graisses fines de l'import (320/330/340/480/540/700) telles quelles ; les
line-heights sont abaissées d'environ 0,02 par rapport à l'import pour compenser la hauteur
d'x d'Inter, comme l'import le recommande.

**Deux échelles, un système.** L'import est calibré pour un site marketing (86px de
display) ; Homeport est un dashboard dense. L'échelle est recalibrée [ASSUMPTION] :

- **Registre landing** — `{typography.display-xl}` (72px) pour le hero,
  `{typography.display-lg}` (52px) pour les ouvertures de section,
  `{typography.body-lg}` pour le corps.
- **Registre app** — `{typography.display}` (40px) pour le verdict du Journal,
  `{typography.headline}` pour les titres de panneaux, `{typography.title}` pour les
  cartes, `{typography.body}` (14px) par défaut, `{typography.body-sm}` pour les notes.
- **Registre données** — `{typography.data-xl}` (Mur, horloge — s'étire en `clamp()` selon
  la hauteur d'écran), `{typography.data-md}` (valeurs de métriques), `{typography.data-sm}`
  (valeurs en table). Tous en `font-variant-numeric: tabular-nums` : les chiffres d'un
  tableau de bord ne doivent jamais danser au rafraîchissement.

**Principes hérités.** La graisse porte la hiérarchie du corps (340 contre 480/540 à taille
égale) ; le tracking négatif croît avec la taille (display serré, corps quasi neutre) ; le
mono est taxonomie, pas lecture — `{typography.eyebrow}` et `{typography.caption}` toujours
en capitales avec tracking positif, pour les étiquettes de section, horodatages, IP, MAC et
noms d'images Docker. Exception assumée : les blocs de logs (`logs-pre`) sont en mono parce
qu'ils citent la machine — c'est une citation, pas du corps de texte. Le chinois (zh)
retombe sur la pile système : Inter ne couvre pas les CJK (voir Open Questions).

## Layout & Spacing

Base 8px, tokens de l'import repris tels quels. Le rythme diverge par registre :

- **Landing** : `{spacing.section}` (96px) entre sections majeures, retour au papier blanc
  entre deux blocs pastel, contenu max ~1280px.
- **App** : rythme vertical `{spacing.xl}` (32px) entre sections, `{spacing.md}` de padding
  intérieur de tuiles, gouttières fluides `clamp(1rem, 4vw, 3rem)` conservées de l'app
  actuelle. [ASSUMPTION sur le rythme 32px.]

Les grilles de l'app restent fluides (`auto-fit, minmax(…)`) : tuiles de métriques
~170px min, cartes de services ~260px min, le Mur en 3 colonnes → 2 (≤820px) → 1 (≤520px).
La vue Contrôle garde sa colonne latérale `minmax(260px, 330px)` qui s'empile sous 900px.

## Elevation & Depth

Système volontairement plat, hérité de l'import : la profondeur vient des surfaces, pas des
ombres.

| Niveau | Traitement | Usage |
|---|---|---|
| 0 (plat) | Aucune ombre, aucune bordure | Blocs pastel, verdict du Journal, pied de page |
| 1 (hairline) | Bordure 1px `{colors.hairline}` | Toutes les tuiles, cartes, inputs, pilules |
| 2 (rail d'état) | Hairline + rail gauche 3px en couleur d'état | `service-card`, `health-tile`, `alert-banner` |
| 3 (modal/scrim) | `{colors.overlay-scrim}` à ~60% | Recouvrements éventuels |

Le rail d'état gauche de 3px est le motif signature conservé de l'app actuelle : il
transpose « la couleur est le dispositif de profondeur » de l'import au vocabulaire d'un
dashboard — c'est le seul endroit où la triade saturée touche une surface. Le halo du Mur
(`box-shadow` doux autour du dot d'état global) est la seule « ombre » du système : c'est
un signal lumineux, pas de l'élévation. Les ombres portées génériques de l'app actuelle
(`--shadow`) disparaissent au profit des hairlines. [ASSUMPTION]

## Shapes

Échelle de l'import conservée intégralement : `{rounded.xs}` 2px (décorations),
`{rounded.sm}` 6px (tags, chips discrets), `{rounded.md}` 8px (tuiles, cartes, inputs,
logs), `{rounded.lg}` 24px (cellules du Mur, blocs pastel, story-block), `{rounded.xl}`
32px (panneaux hero de la landing), `{rounded.pill}` 50px (tout CTA textuel, onglets,
filtres, pilules d'état), `{rounded.full}` (dots, boutons icône circulaires).

La pilule est la seule forme de bouton — aucun bouton carré nulle part, y compris le
bouton de redémarrage. Les dots d'état sont des cercles pleins de 7 à 9px ; le halo du Mur
un cercle de 15px.

## Components

### Navigation

**`top-nav`** — Bandeau d'identité commun aux vues : ancre ⚓, hostname en
`{typography.headline}`, sous-titre en `{typography.body-sm}` `{colors.ink-soft}`, filet
bas `{colors.hairline}`. Hauteur constante d'une vue à l'autre.

**`view-switch-tab-default`** / **`view-switch-tab-selected`** — Le sélecteur des vues
(Classic · Contrôle · Journal · Mur · Réseau · Historique · Livre de bord · Starlink ·
Livebox), transposition directe du pattern pricing-tabs de l'import : l'onglet courant
prend la surface primaire — pilule `{colors.ink}` texte `{colors.canvas}` — exactement
comme un `button-primary`. C'est le remplacement du fond « rouille » actuel : « selected =
primary surface » est la signature de marque. Conteneur en pilule hairline, défilement
horizontal propre sur écran étroit, onglet courant recentré.

### État et signaux

**`state-dot`** — Cercle plein 8px dans une des quatre couleurs d'état. L'unité minimale
de vérité du système ; jamais accompagné de la couleur sur le texte adjacent quand le mot
suffit.

**`state-chip`** — Étiquette d'état des cartes (UP / DÉGRADÉ / ARRÊTÉ) en
`{typography.eyebrow}` : fond teinté à ~16% de la couleur d'état sur `{colors.canvas}`,
texte en variante `state-*-text`. Capitales mono : l'état est une taxonomie.

**`status-pill`** — Compteurs du bandeau (« 12 en ligne ») : pilule hairline blanche,
chiffre en `{typography.data-sm}` coloré en `state-*-text`, mot en encre.

### Tuiles et cartes

**`metric-tile`** — CPU, mémoire, températures, usure SSD, disques : étiquette
`{typography.eyebrow}` `{colors.ink-soft}`, valeur `{typography.data-md}`, note
`{typography.body-sm}`. Barre de progression 4px en `{colors.ink}` sur `{colors.hairline}`
— l'encre remplace l'accent rouille ; la barre ne passe en couleur d'état que si un seuil
est franchi. [ASSUMPTION]

**`health-tile`** — Sauvegardes, APT, images Docker, alimentation, erreurs 24h : même
anatomie que `metric-tile`, plus rail d'état gauche 3px.

**`service-card`** — La tuile de service de la vue Classic. `<details>` natif : tête
(icône, `{typography.title}`, description `{colors.ink-soft}`, `state-chip`, chevron),
panneau déplié (mini-table des sources de vérité Docker/systemd/probe avec valeurs
`ok`/`fail` en `state-*-text`, ligne CPU, disponibilité 7j, actions, tags mono, logs).
Rail d'état gauche 3px. Une carte non-`up` s'ouvre seule.

**`service-row`** — La ligne dense de la vue Contrôle : dot, nom en 480, description
`{colors.ink-soft}` séparée par un filet pointillé, micro-barre CPU, disponibilité et
uptime en `{typography.data-sm}` alignés à droite, filet `{colors.hairline-soft}` entre
lignes.

**`chart-card`** / sparklines — Cartes d'historique : trait `{colors.ink}` 1,5px, aire à
~12% d'encre, bandes de coupure à ~22% de `{colors.state-down}`. Le graphe est
monochrome ; seule la panne a droit à la couleur. [ASSUMPTION]

**`wall-cell`** — Cellule du Mur : `{rounded.lg}`, grand chiffre `{typography.data-xl}` en
`clamp()`, pied `{typography.body-sm}`. En warn/down la bordure se teinte et le chiffre passe
en `state-*-text`.

**L'étiquette du Mur n'est PAS une `{typography.eyebrow}`** — écart délibéré au rôle, mesuré
le 23/08. À la distance de conception (« readable from across a room », PRODUCT.md), une
capitale de 11px en `{colors.ink-soft}` est une texture, pas du texte : le mur affichait six
chiffres géants dont on ne pouvait lire aucun sujet. L'étiquette est donc de l'information de
première classe — `clamp(1rem, 2.4vh, 1.4rem)`, `{typography.weight-strong}`, `{colors.ink}`,
tracking .08em — et le suffixe d'unité quitte `{colors.ink-soft}` pour `{colors.ink}`, faute
de quoi il s'éteint avant le chiffre et « 14 / 15 » se lit « 14 ».

Chaque cellule porteuse d'état affiche en outre **un mot d'état visible** à côté de son
étiquette, teinté en `state-*-text` : l'état ne peut pas tenir à la seule couleur du chiffre
(WCAG 1.4.1). Le mot est propre à la tuile — *dégradé*, *en retard*, *en attente*,
*nouveaux* — jamais dérivé du niveau : les cinq tuiles n'ont pas le même `warn`.

Contenu **groupé au centre** de la cellule, pas écartelé haut/bas : un chiffre séparé de son
étiquette par un vide de 60 % de la tuile se lit d'autant moins de loin.

**Lien rompu** — Au-delà de deux cycles de sondage manqués, le Mur doit *avoir l'air* périmé
de l'autre bout de la pièce : halo en `{colors.state-unknown}` sans lueur, chiffres et mots
d'état désaturés vers `{colors.ink-soft}`, bordures rendues neutres, et la ligne de verdict
remplacée par « hors ligne depuis HH:MM ». Trois états, pas deux : *à jour*, *périmé*, et
*jamais chargé* — une tablette qui redémarre face à un serveur mort n'a aucune donnée
ancienne à conserver. Sans ce traitement le Mur garde un vert périmé pendant des heures
pendant que l'horloge, découplée du sondage, certifie une fraîcheur inexistante.

**Absence gracieuse** — Une tuile dont la source n'existe pas sur la machine (aucune
sauvegarde déclarée, pas de sonde WAN, pas d'APT) **disparaît**. Elle ne porte pas un
avertissement ambre : accuser un foyer de ne pas sauvegarder alors qu'il n'a rien configuré
est un mensonge, pas une alerte.

### Récit

**`verdict`** — Le « Tout va bien. » du Journal : `{typography.display}` en pur
`{colors.ink}`, précédé d'un `state-dot`. Le verdict est typographique, pas coloré — la
phrase porte le jugement, le dot porte le signal. [ASSUMPTION]

**`story-block`** — Le paragraphe narratif du Journal et les états vides habités (livre de
bord vierge) : petit bloc pastel `{rounded.lg}` — crème par défaut, lime pour un livre de
bord vierge — texte `{typography.body-lg}` en encre. C'est le descendant direct des
color-blocks de l'import, à l'échelle du dashboard. Jamais plus d'un par écran ; jamais
corrélé à l'état. [ASSUMPTION]

### Timeline

Livre de bord : en-têtes de jour en `{typography.eyebrow}` soulignés d'un hairline, lignes
(dot d'état, heure en `{typography.caption}`, texte en `{typography.body}`, détail
`{colors.ink-soft}`) séparées par filets pointillés `{colors.hairline-soft}`, logs
dépliables en `logs-pre`.

### Contrôles

**`button-primary`** / **`button-secondary`** — La paire noir/blanc de l'import, padding
recalibré pour l'app (8px 16px). [ASSUMPTION] Landing : padding généreux de l'import.

**`button-danger-armed`** — Le redémarrage en deux temps : au repos, `button-secondary`
avec texte `{colors.state-down-text}` et bordure teintée ; armé, pilule pleine
`{colors.state-down}` texte blanc. Seul bouton du système autorisé à porter une couleur
d'état en fond.

**`filter-pill-default`** / **`filter-pill-selected`** — Filtres du Réseau et du Livre de
bord : même mécanique « selected = primary surface » que le view-switch.

**`text-input`** — Recherche du Réseau, renommage d'appareil : hairline, `{rounded.md}`,
focus par anneau (voir Do's), jamais par changement de fond.

**`select-pref`** — Sélecteurs langue/thème du pied de page : pilules mono discrètes en
`{colors.ink-soft}`.

**`alert-banner`** — Alertes de santé : hairline + rail d'état, fond teinté à ~10% de la
couleur d'état.

**`tag-mono`** / **`logs-pre`** / **`update-chip`** — Tags d'image et de ports en
`{typography.caption}` sur `{colors.surface-soft}` ; logs en bloc mono défilant ; badge de
mise à jour en pilule caption.

**`footer`** — Filet haut, version, horodatage de rafraîchissement, préférences — tout en
`{typography.caption}` `{colors.ink-soft}`.

### Landing (GitHub Pages)

**`landing-hero`** — Hero blanc, `{typography.display-xl}`, paire
`button-primary`/`button-secondary`, ancre ⚓ en marque. **`color-block-section`** — Les
sections pastel pleine largeur de l'import, reprises telles quelles : une couleur par
section, `{rounded.lg}`, `{spacing.xxl}` intérieur, retour au blanc entre deux blocs ;
captures d'écran réelles de l'app (docs/screenshots/) posées dessus en cadres
`{rounded.md}`. `{colors.accent-magenta}` autorisé une fois par page.

## Do's and Don'ts

### Do

- Réserver la triade `{colors.state-*}` aux signaux d'état : dots, chips, rails, verdicts.
  Le pastel `{colors.block-*}` raconte ; le saturé signale. Jamais l'inverse.
- Composer tout CTA et tout onglet en pilule ; « selected = primary surface » (pilule
  encre) pour le view-switch et les filtres.
- Porter la hiérarchie du texte par la graisse d'Inter (340 vs 480/540), pas par la
  taille ; `tabular-nums` sur tout chiffre susceptible de se rafraîchir.
- Réserver JetBrains Mono à la taxonomie (eyebrows, captions, horodatages, IP/MAC, images
  Docker) et aux citations de la machine (logs) — toujours en capitales avec tracking
  positif pour les étiquettes.
- Laisser une intégration absente disparaître en silence — pas de tuile grisée, pas de
  message d'erreur (PRODUCT.md, « graceful absence »).
- Revenir au papier blanc entre deux blocs pastel ; un seul bloc pastel visible par écran
  d'app.
- Garder le grand format lisible de loin sur le Mur : `{typography.data-xl}` en `clamp()`,
  contraste plein `{colors.ink}` sur `{colors.canvas}` dans les deux thèmes.

### Don't

- Ne jamais coder un état par un bloc pastel, ni décorer avec la triade saturée.
- Ne pas introduire d'ombres portées sur les tuiles — hairlines et rails d'état suffisent ;
  la seule lueur permise est le halo d'état du Mur.
- Ne pas étendre `{colors.ink-soft}` au-delà du texte auxiliaire — jamais sur une valeur,
  un verdict ou un état.
- Ne pas utiliser `{colors.accent-magenta}` dans l'app — landing uniquement, un seul par
  page.
- Ne pas équarrir les boutons ni les onglets ; pas de bouton carré nulle part.
- Ne pas charger de police, d'icône ou d'actif depuis un CDN — tout est servi par Homeport.
- Ne pas peindre en vert un état dégradé : si les sources de vérité divergent, l'interface
  montre la divergence (PRODUCT.md, « truth over reassurance »).
- Ne pas mettre JetBrains Mono en corps de texte.

## Open Questions

1. **Couverture CJK** : Inter ne couvre pas le chinois (zh). Pile de fallback système à
   spécifier pour zh (et impact sur le rendu des graisses fines 340/480) — ou embarquer un
   sous-ensemble Noto Sans SC (poids de fichier significatif pour un Raspberry Pi ?).
2. **Instances woff2 à embarquer** : Inter variable (un seul fichier wght) ou instances
   statiques ? Idem JetBrains Mono (400 suffit-il ?). Budget poids à valider pour le
   premier rendu sur tablette murale.
3. **`theme-color` PWA** : actuellement `#b8452f` (rouille). Passer à `#000000` (encre) ou
   `#ffffff` selon thème ? Impacte manifest.json et les meta des templates.
4. **Hex exacts warn/down** : `{colors.state-warn}` et `{colors.state-down}` proposés en
   [ASSUMPTION] ; à valider contre les captures réelles et le lint contrast-ratio (les
   variantes `-text` visent AA, les tokens pleins ne sont pas garantis AA en petit corps).
5. **Pastels sombres** : les sept `block-*-dark` sont des dérivations sans référence
   Figma ; arbitrage visuel au Finalize (notamment `block-lilac-dark` vs `block-navy-dark`,
   proches).
6. **Fond « espace » de la carte Starlink** (`--map-bg` actuel `#101420`) : conservé tel
   quel dans les deux thèmes, ou rattaché à `{colors.block-navy}` ?

---

*Ce spine prime sur tout mock, capture ou import en cas de conflit.*
