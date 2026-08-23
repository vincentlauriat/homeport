---
name: Homeport
description: "Architecture d'information, comportements, états et parcours du dashboard Homeport et de sa landing — la même vérité lue sur un mur, un téléphone et un bureau."
status: final
updated: 2026-08-23
sources:
  - imports/DESIGN-figma.md
  - PRODUCT.md
  - homeport/templates/ + homeport/static/ (l'app en l'état)
---

# Homeport — Experience Spine

## Foundation

Web server-rendered (FastAPI + Jinja2), vanilla JS par vue, une feuille `style.css`
partagée — pas de framework JS, engagement produit durable. `DESIGN.md` (ce workspace) est
la référence visuelle ; ce spine est l'expérience. Trois form-factors de première classe
(PRODUCT.md) :

- **Tablette murale** — la vue Mur tourne en permanence, PWA plein écran, lue à travers la
  pièce.
- **Téléphone via Tailscale** — vérifications rapides et actions en mobilité, écrans
  étroits.
- **Desktop / laptop** — sessions d'admin assises : Contrôle, Historique, diagnostics.

Deux publics à égalité : l'admin self-hosté, et l'inconnu qui installe depuis GitHub —
chaque écran doit rester compréhensible sans contexte maison. Lecture seule sur le LAN ;
les actions (redémarrer, réveiller) n'existent que via Tailscale pour l'admin déclaré.
Mode démo (`HOMEPORT_DEMO=1`) : tout écran se rend sur données simulées. Thèmes
clair/sombre/auto, i18n en/fr/zh.

## Information Architecture

Sept vues d'app (plus deux conditionnelles) partagent une même nav (`view-switch`), et
sont des lectures différentes d'un même dataset — pas des produits différents
(PRODUCT.md, « same truth, four registers »).

| Surface | Route | Atteinte depuis | Rôle |
|---|---|---|---|
| Classic | `/` | défaut, nav | Vue complète : métriques machine, alertes, tuiles santé, mini-historique, réseau, cartes de services dépliables |
| Contrôle | `/controle` | nav | Salle de contrôle dense : pilules de synthèse, panneaux machine/santé/réseau, tables de services par groupe |
| Journal | `/journal` | nav | Récit : verdict (`{components.verdict}`), histoire du jour (`{components.story-block}`), faits, listes calmes |
| Mur | `/mur` | nav, PWA | Horloge, état global à halo, 6 grandes cellules (`{components.wall-cell}`) lisibles de loin |
| Réseau | `/reseau` | nav, tuile LAN de Classic | Inventaire des appareils : nouveaux à valider, recherche, filtres, renommage, notes |
| Historique | `/historique` | nav, lien mini-historique | 7 jours de courbes avec bandes de coupure, légende |
| Livre de bord | `/livre-de-bord` | nav | Timeline des événements par jour, filtres famille + période |
| Starlink | `/starlink` | nav (si module actif), tuile réseau | Détail liaison : cellules, carte d'obstruction, débit |
| Livebox | `/livebox` | nav (si module actif), tuile réseau | Détail box opérateur |
| Landing | GitHub Pages | README, web | Présentation du produit : hero, sections pastel (`{components.color-block-section}`), captures réelles, installation |

Starlink et Livebox n'apparaissent dans la nav que si le module est actif — l'absence est
invisible, pas grisée. Le view-switch défile horizontalement sur écran étroit et recentre
l'onglet courant au chargement. Pas de modale dans l'app : le drill-down passe par des
`<details>` natifs et des pages dédiées.

→ Référence de composition : `docs/screenshots/` (captures réelles) et le mode démo. Le
spine prime en cas de conflit.

## Voice and Tone

Microcopy. La voix visuelle vit dans `DESIGN.md`. Ton : calme, narratif, humain — le
Journal parle comme un livre de bord, jamais comme un moniteur. Trilingue en/fr/zh : toute
chaîne UI passe par `homeport/i18n/*.json`, dans les trois langues, aucune chaîne en dur.

| Do (existant dans l'app) | Don't |
|---|---|
| « Tout va bien. » / "All is well." | « ✅ Tous les systèmes opérationnels ! » |
| « Presque tout va bien. » | « Attention : anomalies détectées » |
| « la maison a été sauvegardée il y a 3 h » | « Backup job #142 : SUCCESS » |
| « hors ligne — dernière vue conservée » | « Erreur réseau » |
| « Le livre de bord est vierge — les événements s'écriront au fil de la vie du port. » | « Aucune donnée disponible » |
| « pas encore mesuré » | « N/A » ou une tuile en erreur |

Règles : phrases courtes et complètes ; le vocabulaire nautique reste léger (port, journal,
mur, livre de bord) et ne bascule jamais dans le thématique forcé ; les nombres disent la
vérité (« 2 services en panne. » en verdict, pas d'euphémisme) ; pas d'exclamation, pas
d'emoji dans le texte courant (les icônes de services et 🛰️/📡 des tuiles sont des
pictogrammes, pas du ton).

## Component Patterns

Comportemental. Les specs visuelles vivent dans `DESIGN.md` (§Components).

| Composant | Usage | Règles comportementales |
|---|---|---|
| `view-switch` | Toutes les vues | Onglet courant = pilule encre. Défilement horizontal contenu (jamais la page), recentrage auto de l'onglet courant. Rendu identique sur toutes les vues. |
| `service-card` | Classic | `<details>` natif. S'ouvre seule si l'état ≠ up — la raison est visible sans clic exactement quand elle compte. Tête cliquable entière. Logs chargés à la demande au dépliage. |
| `service-row` | Contrôle | Ligne dense, lien vers l'URL du service sur le nom. Colonnes fixes partagées entre groupes pour l'alignement inter-tables. Sous 640px : description et disponibilité disparaissent. |
| Mini-table des sources | `service-card` dépliée | Une ligne par source de vérité (Docker, systemd, probe) avec valeur ok/fail — la divergence entre sources est montrée, jamais résumée en vert. |
| `button-danger-armed` | Cartes restartables | Deux temps : premier tap arme (pilule pleine `{colors.state-down}`), second tap dans les ~5 s exécute, sinon désarmement. Résultat en `role="status"`. Visible uniquement pour l'admin Tailscale. [ASSUMPTION sur le délai] |
| Filtres (`filter-pill-*`) | Réseau, Livre de bord | Sélection exclusive par groupe (famille / période). Filtre actif = pilule encre. |
| Renommage d'appareil | Réseau | Nom cliquable → input inline, blur/Enter enregistre, Esc annule. [ASSUMPTION sur Esc] |
| `story-block` | Journal, états vides | Au plus un par écran. Couleur pastel fixe par usage, jamais liée à l'état. |
| `wall-cell` | Mur | Chiffre en `clamp()` selon hauteur d'écran ; bascule warn/down par bordure teintée + valeur en `state-*-text`. |
| `select-pref` | Pied de page, toutes vues | Langue : cookie + rechargement (rendu serveur). Thème : localStorage + `data-theme` immédiat, sans rechargement. |
| `update-chip` | Pied de page | N'apparaît que si une mise à jour existe ; lien discret, jamais de nag. |

## State Patterns

Quatre états de service — up / warn / down / unknown — portés par la triade
`{colors.state-up}` / `{colors.state-warn}` / `{colors.state-down}` /
`{colors.state-unknown}` et leurs variantes texte `{colors.state-up-text}`,
`{colors.state-warn-text}`, `{colors.state-down-text}` (AA en petit corps).

| État | Surface | Traitement |
|---|---|---|
| Chargement initial | Vues JS (Contrôle, Journal, Mur…) | Tirets « — » aux emplacements de valeurs + « chargement… » ; jamais de spinner plein écran, la structure est visible immédiatement. |
| Rafraîchissement périodique | Toutes | Mise à jour en place, chiffres stables (`tabular-nums`), pied de page « actualisé à l'instant / à {time} ». |
| Hors ligne (client) | Toutes | « hors ligne — dernière vue conservée ({error}) » dans le pied ; la dernière vérité connue reste affichée, rien ne s'efface. |
| Warn / degraded | Cartes, tuiles, Mur | Rail/bordure `{colors.state-warn}`, chip DÉGRADÉ, carte auto-ouverte sur la divergence de sources. Jamais peint en vert. |
| Down | Idem + verdict | Verdict Journal : « {count} service(s) en panne. » ; Mur : halo `{colors.state-down}`. Alerte bannière en tête de Classic. |
| Unknown / pas mesuré | Tuiles santé | « — » + « pas encore mesuré » en `{colors.ink-soft}` ; l'absence de mesure n'est pas une erreur. |
| Intégration absente | Partout | La tuile/l'entrée de nav disparaît, silencieusement (graceful absence). Pas d'état « non configuré ». |
| Vide habité | Livre de bord | `story-block` lime : « Le livre de bord est vierge… ». |
| Nouveaux appareils LAN | Réseau, badge sur Classic | Panneau « nouveaux » à rail `{colors.state-warn}` + badge `chip-new` sur la tuile LAN ; l'admin acquitte pour les faire entrer dans l'inventaire. |
| Action en cours / résultat | Cartes restartables | Bouton désactivé pendant l'exécution ; résultat inline ok/fail en `state-*-text`, annoncé par `role="status"`. |

## Interaction Primitives

- **Tap/clic d'abord.** Pas de raccourcis clavier applicatifs [ASSUMPTION : non prioritaire
  — publics tablette/téléphone] ; tout est atteignable au clavier standard (Tab/Enter).
- **`<details>/<summary>` natifs** pour tout drill-down (cartes, logs, voisins LAN) —
  dépliage sans JS, état préservé par le navigateur.
- **Actions destructives en deux temps** (armer puis confirmer) plutôt qu'en modale.
- **Polling doux** : l'app se rafraîchit périodiquement en place ; jamais de rechargement
  de page sauf changement de langue.
- **Cibles tactiles ≥ 44px** sur pointeur grossier (media query `pointer: coarse`) sans
  changer le rendu au pointeur fin.
- **Bannis** : modales empilées, infinite scroll, hover-only (tout hover a un équivalent
  tap), sons, notifications push, animation d'apparition sur le Mur (il tourne 24h/24).

## Accessibility Floor

L'app possède déjà un socle — il est préservé et devient exigence minimale :

- **Focus visible** : `:focus-visible` en anneau 2px décalé de 2px, couleur `{colors.ink}`
  dans le nouveau système [ASSUMPTION : l'anneau actuel est accent rouille], identique dans
  les deux thèmes.
- **`prefers-reduced-motion`** : animations de barres et chevrons gelées ; les changements
  de couleur d'état restent (feedback sans mouvement).
- **Lecteurs d'écran** : `.sr-only` pour les titres implicites (Mur), `aria-live="polite"`
  sur les zones re-rendues (Livre de bord), `role="status"` sur les résultats d'action,
  `aria-hidden` sur les pictogrammes décoratifs, `aria-label` sur les sélecteurs de
  préférences.
- **`lang`** posé sur `<html>` selon la langue servie ; `meta color-scheme` light dark.
- **Cibles tactiles** ≥ 44px au doigt (voir Interaction Primitives).
- **Contraste** : AA (4.5:1) pour tout texte courant dans les deux thèmes — c'est la raison
  d'être des tokens `state-*-text` ; les tokens d'état pleins sont réservés aux surfaces
  non textuelles (dots, rails, fonds). Le Mur vise mieux que AA : grands chiffres en
  `{colors.ink}` plein sur `{colors.canvas}` (lecture à distance, PRODUCT.md).
- **Jamais d'information portée par la couleur seule** : chaque état a son mot (chip,
  verdict, note) en plus de sa couleur.

## Key Flows

### Flow 1 — Le coup d'œil de 2h du matin (Vincent, insomnie, couloir) [ASSUMPTION : protagoniste et scénario plausibles]

1. Vincent passe devant la tablette murale en allant boire un verre d'eau.
2. Le Mur affiche l'heure en `{typography.data-xl}`, et à droite le halo d'état global.
3. Le halo est vert (`{colors.state-up}`), le texte dit « Tout va bien ».
4. **Climax :** il n'a rien touché, rien lu d'autre. Six grandes cellules, un halo, trois
   secondes — la réponse à « est-ce que tout va bien ? » a traversé la pièce avant lui.
   Il retourne se coucher.

Échec : le halo est ambre — la cellule fautive (Sauvegarde, « il y a 26 h ») est teintée
`{colors.state-warn}` et lisible du couloir. Il décide que ça attend demain, en
connaissance de cause. Le Mur ne bipe pas, ne clignote pas : il dit, c'est tout.

### Flow 2 — Redémarrage depuis le train (Vincent, téléphone, Tailscale) [ASSUMPTION]

1. Message de la maison : « Jellyfin ne marche plus ». Vincent ouvre Homeport via
   Tailscale sur son téléphone.
2. Classic s'ouvre : bannière d'alerte en tête, la carte Jellyfin est déjà dépliée
   (état ≠ up ⇒ auto-ouverte) sur sa mini-table : Docker `running`, probe HTTP `fail` —
   la divergence est visible, le conteneur tourne mais ne répond pas.
3. Identifié admin par `tailscale whois`, il voit la rangée d'action. Premier tap :
   « Redémarrer » s'arme en pilule pleine `{colors.state-down}`. Deuxième tap : exécution.
4. Le résultat s'affiche inline (« ok » en `{colors.state-up-text}`), annoncé par
   `role="status"`.
5. **Climax :** au rafraîchissement suivant, le chip repasse UP, la carte se referme au
   prochain chargement, et le Livre de bord a écrit la ligne — l'action, son auteur, son
   heure. La maison est réparée depuis un train, et le port en garde la trace.

Échec : le restart échoue → résultat « fail » en `{colors.state-down-text}`, la carte
reste ouverte sur les logs dépliables du conteneur. Pas de retry automatique : c'est
l'admin qui décide.

### Flow 3 — Elena installe Homeport (inconnue, GitHub, samedi après-midi) [ASSUMPTION]

1. Elena cherche un dashboard pour son Raspberry Pi et tombe sur la landing GitHub Pages :
   hero `{typography.display-xl}`, sections `{components.color-block-section}` avec les
   captures réelles des quatre vues, section installation sur bloc lime.
2. Elle lance le mode démo (`HOMEPORT_DEMO=1`) — le dashboard complet se rend sur données
   simulées, identique aux captures.
3. Elle branche sa config YAML : ses trois conteneurs apparaissent. Pas de Starlink, pas
   de Tailscale → ces tuiles n'existent simplement pas ; rien ne réclame.
4. **Climax :** la première vue qu'elle épingle sur sa tablette est le Mur — et il dit
   « All is well » dans sa langue, sans qu'elle ait rien configuré d'autre. Le produit
   qu'elle a vu sur la landing est exactement celui qu'elle fait tourner : mêmes pilules,
   même encre, mêmes états.

Échec : sa machine n'a pas de capteur de température → la tuile affiche « pas encore
mesuré » puis disparaît de ses préoccupations ; aucun message d'erreur ne lui fait croire
que son installation est cassée.

## Responsive & Platform

Breakpoints adaptés du système importé au contexte app (l'import vise un site marketing ;
l'app garde ses seuils éprouvés) :

| Seuil | Comportement |
|---|---|
| ≥ 1280px (desktop) | Contenu landing max 1280px, gouttières croissantes. App : grilles fluides pleine largeur, Contrôle en deux colonnes. |
| ≤ 960px (landing) | Sections pastel : marges réduites. Nav landing repliée. [ASSUMPTION] |
| ≤ 900px (app) | Contrôle passe en une colonne. |
| ≤ 820px | Mur : 3 → 2 colonnes. |
| ≤ 768px (landing) | Blocs pastel à fond perdu (coins non arrondis aux bords), effet poster — repris de l'import. |
| ≤ 720px | Réseau : méta des lignes repliée sous le nom. |
| ≤ 640px | Contrôle : colonnes description/disponibilité masquées. Journal : faits en 2 colonnes. |
| ≤ 520px | Classic : cartes en une colonne. Mur : une colonne. View-switch défile. |

PWA : installable, plein écran sur la tablette murale ; `manifest.json` et
`theme-color` à réaligner sur la nouvelle identité (voir Open Questions de DESIGN.md).
Le Mur doit rester correct en paysage comme en portrait sur tablette. Offline strict :
aucune ressource externe sur aucune page.

## Inspiration & Anti-patterns

- **Repris de l'import Figma** : « selected = primary surface » (le view-switch est un
  pricing-tab), le retour au blanc entre blocs pastel, la hiérarchie par la graisse.
- **Repris de l'app actuelle** : l'auto-ouverture des cartes en panne, le restart en deux
  temps, la disparition silencieuse des intégrations absentes, les `<details>` natifs —
  des comportements éprouvés que la nouvelle peau ne doit pas casser.
- **Rejeté — le dashboard-cockpit** (Grafana et consorts) : pas de mur de graphes, pas de
  densité pour la densité. Le verdict d'abord, le détail sur demande.
- **Rejeté — la gamification et le rassurisme** : pas de score de santé synthétique, pas
  de « 99,9 % 🎉 ». Les pourcentages de disponibilité sont des faits datés, pas des
  trophées.
- **Rejeté — le pastel sémantique** : la tentation de teinter le Journal en lime quand
  tout va bien. Les blocs racontent, les signaux signalent — c'est la ligne rouge du
  système.

## Open Questions

1. Le délai de désarmement du bouton restart (proposé ~5 s) et son annonce aux lecteurs
   d'écran (le changement armé/désarmé doit-il être verbalisé ?).
2. La landing GitHub Pages n'existe pas encore : périmètre exact des sections (features,
   installation, captures, FAQ ?) à cadrer — ce spine ne fixe que son langage visuel et
   son rôle d'entrée vers le README.
3. Le Mur la nuit : faut-il un mode « veilleuse » (luminosité réduite au-delà du thème
   sombre) pour une tablette allumée en permanence dans un couloir ?
4. Comportement du view-switch à 9 entrées (Starlink + Livebox actifs) sur téléphone
   étroit : le défilement suffit-il, ou faut-il un débordement « ⋯ » ?

---

*Ce spine prime sur tout mock, capture ou import en cas de conflit.*
