# Réconciliation — imports/DESIGN-figma.md → spines Homeport

Comment l'analyse du design system marketing de Figma (import utilisateur) a été
distillée dans `DESIGN.md` et `EXPERIENCE.md`. Rappel memlog : ce système REMPLACE
l'identité « Harbormaster's Desk » (DESIGN.md racine, exclu des sources).

## Repris tel quel

- **Le cœur monochrome** : `ink` #000000 / `canvas` #ffffff, hairlines #e6e6e6 /
  #f1f1f1, `surface-soft` #f7f7f5, encre inverse — hex identiques.
- **Les sept blocs pastel** (`block-lime/lilac/cream/pink/mint/coral/navy`) et
  `accent-magenta`, hex identiques (l'import les signale déjà comme approximations
  fidèles issues de captures).
- **La pilule comme seule forme de bouton** (`rounded.pill`), et la paire signature
  `button-primary` noir / `button-secondary` blanc.
- **L'échelle de rayons complète** (2/6/8/24/32/50/9999) et **l'échelle d'espacement
  base 8** (hair→section 96px), tokens inchangés.
- **Le pattern « selected = primary surface »** (pricing-tab-selected) — devenu le
  comportement du `view-switch` et des filtres de l'app.
- **Mono = taxonomie** : eyebrows/captions en capitales, tracking positif, jamais en
  corps de texte.
- **La hiérarchie par la graisse** (320–700), le tracking négatif croissant avec la
  taille, les line-heights serrées en display.
- **L'élévation sans ombres** : hairline plutôt qu'ombre portée, la couleur comme
  dispositif de profondeur ; le scrim ~60%.
- **Le rythme landing** : sections de 96px, retour au blanc entre blocs, blocs à fond
  perdu sous 768px, `color-block-section` transposé tel quel sur la landing GitHub
  Pages ; `semantic-success` #1ea64a réutilisé comme `state-up`.

## Adapté (et comment)

- **figmaSans/figmaMono → Inter variable / JetBrains Mono** (décision memlog, substituts
  recommandés par l'import lui-même), embarquées en woff2, offline strict. Graisses fines
  320/330/340/480/540/700 conservées sur l'axe wght continu d'Inter ; line-heights
  abaissées de ~0,02 comme le préconise l'import.
- **Échelle typographique recalibrée pour un dashboard** : display 86→72px (landing) et
  40px (verdict app), corps 18→14px, plus un registre `data-*` en `tabular-nums` (Mur,
  métriques) qui n'existait pas dans l'import marketing. Tout tagué [ASSUMPTION].
- **`semantic-success` étendu en triade d'état** up/warn/down/unknown + variantes `-text`
  assises vers l'encre pour l'AA en petit corps (motif repris de l'app actuelle). Hors
  palette pastel — décision memlog. Hex warn/down proposés [ASSUMPTION].
- **Dark mode dérivé de zéro** : l'import n'en documente pas (« le navy et le footer
  inversé sont le seul analogue »). Encre inversée + pastels assombris à teinte
  constante, tous tokens `-dark` en [ASSUMPTION] pour arbitrage au Finalize.
- **Color-blocks rétrogradés dans l'app** : de sections pleine page (marketing) à
  `story-block` compact (récit du Journal, états vides), au plus un par écran, jamais
  corrélé à l'état. Pleine taille uniquement sur la landing.
- **La règle « pas de gris moyen » assouplie** : l'app introduit un unique `ink-soft`
  pour le texte auxiliaire (notes, descriptions, horodatages) — un dashboard dense ne
  tient pas avec la seule graisse comme hiérarchie. Écart assumé et borné (jamais sur une
  valeur, un verdict ou un état). [ASSUMPTION]
- **Paddings de boutons réduits** (10px 20px → 8px 16px) pour la densité app ; la landing
  garde les paddings de l'import.
- **Le rail d'état gauche 3px** (motif de l'app actuelle, absent de l'import) conservé et
  reformulé dans le langage du système : c'est le seul point de contact entre la triade
  saturée et une surface.
- **`accent-magenta` restreint** : conservé mais landing uniquement, un par page (l'import
  disait déjà « single-shot ») ; interdit dans l'app.

## Écarté (et pourquoi)

- **`marquee-strip`** (ruban défilant de logos clients) : dispositif marketing sans
  équivalent dashboard ; Homeport n'a ni clients ni bandeau animé (le Mur tourne 24h/24,
  memlog anti-animation).
- **`pricing-tabs` / `pricing-card` / matrice de comparaison / `comparison-checkmark`** :
  pas de pricing — mais la mécanique selected/default des tabs survit dans le
  view-switch, et le check vert survit en `state-up`.
- **`promo-banner-lilac` + `button-magenta-promo`** en tant que composants : pas de
  promos dans un outil self-hosté ; seul le token magenta survit pour la landing.
- **Sticky-notes inclinées et mocks produit flottants** (FigJam) : signature de marque
  Figma, pas transposable — les captures réelles de Homeport les remplacent, posées à
  plat en cadres 8px.
- **Animations au scroll et lazy-reveal** : proscrites sur un dashboard permanent et une
  tablette murale ; non documentées par l'import de toute façon.
- **display-xl 86px et section 96px dans l'app** : conservés côté landing seulement ;
  l'app est un instrument, pas un poster.

## Idées qualitatives de l'import à ne pas perdre

Ces principes de prose risquaient de disparaître à la distillation — ils sont désormais
ancrés dans les spines :

1. **« Le monochrome rend les blocs intentionnels, les blocs rendent le monochrome
   éditorial »** — le contraste structurel des deux registres est la marque ; d'où la
   ligne rouge « le pastel raconte, le saturé signale ».
2. **« Un seul bloc de couleur par viewport »** — transposé en « au plus un story-block
   par écran d'app ».
3. **« Si deux button-primary apparaissent dans le même viewport, la section en fait
   trop »** — repris via la rareté de la pilule encre (un seul onglet sélectionné, un
   seul CTA primaire).
4. **« La couleur est le dispositif de profondeur »** — réinterprété en rail d'état 3px
   et halo du Mur, seules « élévations » colorées du système.
5. **« Weight, not size, carries hierarchy »** — conservé, avec l'assouplissement
   `ink-soft` documenté comme écart et non comme oubli.

---

*Les spines (`DESIGN.md`, `EXPERIENCE.md`) priment sur cet import et sur tout mock en cas
de conflit.*
