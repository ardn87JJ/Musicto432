# Calibration sur des morceaux réels

Le dépôt ne contient aucun morceau protégé. Le banc de calibration travaille avec des références que vous possédez, avez créées ou êtes autorisé à analyser.

## Préparer le jeu de référence

Créer deux dossiers en dehors du dépôt :

```text
references-accordage/
├── 432/
│   ├── morceau-reference-1.wav
│   └── morceau-reference-2.flac
└── 440/
    ├── morceau-reference-1.wav
    └── morceau-reference-2.flac
```

Choisir de préférence des morceaux contenant des instruments acoustiques ou des notes tenues. Éviter de constituer tout le jeu avec un seul titre simplement transposé : plusieurs productions, styles et timbres permettent une calibration plus honnête.

## Exécuter

Après avoir activé l’environnement Python du backend :

```bash
python scripts/calibrate-tuning.py "$HOME/Musique/references-accordage" \
  --json "$HOME/Téléchargements/calibration-musicto432.json"
```

Le rapport donne, pour chaque morceau, la fréquence estimée, l’erreur absolue, la classification, la confiance et le diagnostic. Une erreur moyenne faible sur plusieurs titres indépendants est plus significative qu’un résultat parfait sur une sinusoïde.

## Interprétation

- `classified_correctly` doit se rapprocher du nombre total de références ;
- `mean_absolute_error_hz` mesure l’écart moyen avec la référence annoncée ;
- une confiance faible récurrente sur un style révèle une limite du détecteur ;
- les morceaux percussifs ou à hauteur instable doivent produire un diagnostic explicite plutôt qu’une fausse certitude.
