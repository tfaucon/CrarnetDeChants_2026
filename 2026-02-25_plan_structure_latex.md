# Plan : Structure LaTeX du Carnet de Chants SGDF Tassin

## Contexte
Créer la structure LaTeX d'un carnet de chants A5 pour les Scouts et Guides de France de Tassin, avec accords de guitare au-dessus des paroles, style sobre noir et blanc, 96 chants en 5 thèmes.

## Choix techniques
- **Package `songs`** (mode `chorded`) : conçu pour les carnets de chants avec notation `\[accord]` au-dessus des paroles
- **Format A5**, two-side, 2 colonnes pour maximiser l'espace
- **Style sobre** : noir et blanc, typographie classique, sans numéros de chants

## Structure des fichiers

```
Scouts/
├── main.tex                  # Document maître
├── Makefile                  # Compilation multi-passe (pdflatex + songidx)
├── preamble/
│   ├── packages.tex          # Imports (songs, geometry, babel, fancyhdr, hyperref)
│   ├── layout.tex            # Géométrie A5, marges 10-12mm, 2 colonnes, en-têtes
│   ├── fonts.tex             # Polices : sans-serif compact pour paroles, gras pour accords
│   ├── songconfig.tex        # Espacement serré (versesep=4pt, baselineadj=-2pt, etc.)
│   └── commands.tex          # \songsection redéfini pour pages de séparation thématiques
├── frontmatter/
│   └── titlepage.tex         # Page de titre
├── songs/
│   ├── sgdf.tex              # LES SGDF (29 chants)
│   ├── benedicite.tex        # BÉNÉDICITÉ (8 chants)
│   ├── coindufeu.tex         # COIN DU FEU (37 chants)
│   ├── coindufeu_anglais.tex # COIN DU FEU ANGLAIS (10 chants)
│   └── tempsspi.tex          # TEMPS SPI (17 chants)
├── backmatter/
│   └── index.tex             # Index alphabétique des chants (3 colonnes)
└── build/                    # Artefacts de compilation (gitignored)
```

## Fichiers à créer (dans l'ordre)

1. **`preamble/packages.tex`** — inputenc, fontenc, babel[french,english], songs[chorded], geometry[a5paper], fancyhdr, hyperref
2. **`preamble/layout.tex`** — `\songcolumns{2}`, marges 10-12mm, headers avec fancyhdr
3. **`preamble/fonts.tex`** — `\lyricfont{\sffamily\small}`, `\stitlefont{\bfseries\large}`, `\printchord` en gras
4. **`preamble/songconfig.tex`** — `\nosongnumbers`, `\noversenumbers`, versesep=4pt, cbarwidth=1pt
5. **`preamble/commands.tex`** — `\songsection` redéfini (page entière centrée avec titre + filet)
6. **`frontmatter/titlepage.tex`** — Titre sobre, nom du groupe, année
7. **`songs/sgdf.tex`** — 29 chants avec structure `\beginsong{Titre}[by={Auteur}]` + `\beginverse`/`\beginchorus` + `\[accords]`
8. **`songs/benedicite.tex`** — 8 chants courts
9. **`songs/coindufeu.tex`** — 37 chants
10. **`songs/coindufeu_anglais.tex`** — 10 chants, enveloppés dans `\begin{otherlanguage}{english}`
11. **`songs/tempsspi.tex`** — 17 chants
12. **`backmatter/index.tex`** — `\showindex[3]{Index des chants}{titleidx}`
13. **`main.tex`** — Assemble tout avec `\newindex`, `\input` dans l'ordre
14. **`Makefile`** — 3 passes pdflatex + songidx.lua entre les passes

## Format d'un chant (exemple)

```latex
\beginsong{Imagine}[by={John Lennon}]
\beginverse
\[C]Imagine there's \[F]no heaven,
\[C]It's easy if \[F]you try.
\endverse
\beginchorus
\[F]You may \[G]say I'm a \[C]dreamer,
\[F]But I'm \[G]not the only \[C]one.
\endchorus
\endsong
```

## Première étape
Créer la structure LaTeX **sans les paroles ni accords** dans les fichiers `songs/*.tex` — juste les `\beginsong{Titre}[by={...}]` / `\endsong` pour chaque chant, avec un commentaire `% TODO: ajouter paroles et accords`. Cela permet de valider la compilation et le rendu avant d'ajouter le contenu.

## Vérification
1. `make` dans le répertoire Scouts/ → doit compiler sans erreur
2. Le PDF généré doit être en A5, 2 colonnes, avec les 5 sections séparées
3. L'index alphabétique doit lister les 96 titres
4. Les pages de séparation thématiques doivent apparaître
