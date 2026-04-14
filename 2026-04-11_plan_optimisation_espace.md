# Plan : Optimisation de l'espace et réduction des zones blanches

## Contexte
Le carnet de chants fait actuellement 136 pages (A5 paysage, `\songcolumns{3}` global dans `preamble/layout.tex:12`). De nombreuses pages présentent des zones blanches importantes, causées par :
- les chants forcés à démarrer en haut de colonne/page (`\songpos` par défaut),
- un nombre de colonnes uniforme mal adapté à la longueur des lignes de chaque chant,
- la dernière page de chaque section non équilibrée.

Contrainte unique : garder les chants **différentiables et lisibles**.

## Stratégie (ordre croissant de coût)

### 1. Relaxer le placement des chants (gain rapide majeur)
Ajouter `\songpos{0}` dans `preamble/songconfig.tex`. Par défaut, le package `songs` place chaque chant en haut de colonne, ce qui est la source principale des blancs de queue. La barre de refrain verte et le titre `\stitle` suffisent à distinguer visuellement les chants consécutifs.

### 2. Colonnes par chant, basées sur la largeur du texte
Plus les lignes sont longues, moins il faut de colonnes.

**Mécanisme** : définir un wrapper `\songcols{N}` dans `preamble/commands.tex` qui appelle `\songcolumns{N}` entre deux chants (le package ne permet pas de changer de colonnage à l'intérieur d'un chant).

**Heuristique validée par mesure** (voir § Analyse de distribution) :
- Distribution unimodale centrée sur ~50 caractères.
- 72 % des chants tiennent dans la plage 41–70 → 3 colonnes par défaut.
- 8 chants seulement (3,7 %) dépassent 70 caractères → à taguer individuellement.
- La section `benedicite` est homogène (max 42) → override au niveau section.

**Deux interventions ciblées suffisent** :

#### 2a. Override section pour `benedicite`
Dans `main.tex`, entourer l'input de `benedicite` :
```latex
\songcolumns{4}
\input{songs/benedicite}
\songcolumns{3}
```
Gain attendu : section qui passe de plusieurs pages à une ou deux.

#### 2b. Tagging manuel des 8 outliers

| Largeur | Chant | Colonnes suggérées |
|---:|---|:---:|
| 120 | `coindufeu/30_j_ai_une_tante_au_maroc` | 1 (+ couper manuellement la ligne-gag de 120 car.) |
| 83  | `sgdf/32_la_scoutitude` | 1 |
| 81  | `tempsspi/18_regardez_l_humilite_de_dieu` | 1 ou 2 |
| 77  | `coindufeu/49_les_prisons_de_nantes` | 2 |
| 75  | `sgdf/30_clameurs_du_monde` | 2 |
| 72  | `sgdf/18_le_monsieur_en_chemise` | 2 |
| 70  | `sgdf/29_la_scoutance` | 2 (borderline) |
| 70  | `coindufeu/46_formidable` | 2 (borderline) |

Ajouter `\songcols{N}` avant chaque `\beginsong` concerné.

**Ce qui n'est PAS nécessaire** grâce à la distribution mesurée :
- Pipeline LaTeX deux-passes de mesure précise : la marge entre les outliers (77–120) et le seuil (~65) absorbe l'imprécision du comptage caractères.
- Réordonnancement des chants par colonnage : seulement 9 transitions au total (benedicite + 8 outliers), donc pas de thrashing.
- Percentile 95 au lieu du max : un seul chant ("J'ai une tante au Maroc") a une ligne-gag aberrante, à traiter manuellement.

### 3. Micro-typographie
Ajustements dans `preamble/songconfig.tex` :
- `\versesep` : 5pt → 3pt plus 2pt minus 1pt
- Augmenter `\emergencystretch` pour absorber les lignes borderline en 3 colonnes sans overfull box.
- Resserrer l'inter-chant quand `\songpos{0}` est actif.

Chaque modification : 1 ligne, mesurer l'impact après chaque.

### 4. Équilibrage de fin de section
Appeler `\balancecolumns` avant chaque `\songsectionpage` pour éviter les dernières pages à moitié vides.

### 5. Nettoyage préalable (hors plan mais recommandé)
`songs/deprecated/` contient 81 doublons non inclus dans le PDF. Confirmer avec l'équipe s'il faut le supprimer — indépendant de ce plan mais source de confusion.

## Analyse de distribution (mesurée le 2026-04-11)

Script : comptage caractères après strip de `\[...]`, `\textnote{}`, `\musicnote{}` et commandes LaTeX. 136 chants live, 81 dans `deprecated/`.

```
  ≤40 :  56 chants  (26 %)  — candidats 4 colonnes
 41-55 : 101 chants  (47 %)  — 3 colonnes OK
 56-70 :  52 chants  (24 %)  — 3 colonnes, borderline
  >70 :   8 chants  ( 4 %)  — 1 ou 2 colonnes
```

Par section (longueur max de ligne, caractères) :

| Section | n | min | médiane | p95 | max |
|---|---:|---:|---:|---:|---:|
| `benedicite` | 8 | 31 | 40 | 42 | **42** |
| `coindufeu` | 60 | 28 | 51 | 70 | 120 |
| `coindufeu_anglais` | 14 | 40 | 54 | 67 | 67 |
| `sgdf` | 35 | 27 | 52 | 75 | 83 |
| `tempsspi` | 19 | 35 | 51 | 81 | 81 |

**Conclusion** : distribution unimodale, pas bimodale. Valide l'approche "défaut 3 colonnes + quelques overrides ciblés" plutôt qu'un clustering par largeur.

## Downsides identifiés et mitigations

1. **Mesure caractères imprécise** (ignore métrique des polices, chords au-dessus des lyrics). *Mitigation* : marge confortable entre outliers et seuil → erreur de 20 % n'affecte pas la classification.
2. **Une ligne outlier démote tout un chant.** *Mitigation* : casser manuellement la ligne-gag de "J'ai une tante au Maroc".
3. **Densité verticale non prise en compte** (les chants riches en accords sont ~1,8× plus hauts). *Mitigation* : étape 3 (micro-typo) compense partiellement.
4. **Transitions de colonnage coûtent un peu de blanc.** *Mitigation* : seulement 9 transitions au total, négligeable.
5. **`\textnote`, `\musicnote`, `by={...}` augmentent la largeur** sans apparaître dans le strip. *Mitigation* : les 8 chants outliers sont de toute façon taggés manuellement, vérification visuelle après build.
6. **Dérive maintenance** : nouveau chant = nouvelle mesure. *Mitigation* : ajouter le script de distribution dans `Makefile` (cible `make stats`) pour recontrôle facile.

## Exécution (ordre recommandé)

1. **Baseline** : noter le nombre de pages actuel par section. Commit.
2. **Étape 1** seule (`\songpos{0}`) → rebuild → mesurer delta.
3. **Étape 3** seule (micro-typo) → rebuild → mesurer delta.
4. **Étape 2a** (benedicite 4 colonnes) → rebuild → vérifier visuellement.
5. **Définir `\songcols{N}`** dans `preamble/commands.tex`.
6. **Étape 2b** (tagging des 8 outliers) → rebuild → vérifier visuellement.
7. **Casser la ligne-gag** de "J'ai une tante au Maroc" → rebuild.
8. **Étape 4** (balancing) → rebuild.
9. **Revue visuelle finale** : scanner le PDF, identifier les pages restantes avec >30 % de blanc, ajuster au cas par cas.

## Cible

- **≤120 pages** (vs 136 actuelles, soit ~12 % de gain).
- Aucun overfull box dans le log.
- Tous les chants gardent titre visible et barre de refrain intacte.
- Chaque chant reste clairement séparé du suivant.

## Validation à chaque étape

- `pdfinfo build/main.pdf | grep Pages` → suivre l'évolution.
- `grep -i overfull build/main.log` → vérifier l'absence de régression typographique.
- Revue visuelle du PDF (focus sur les transitions de section et les chants taggés).
