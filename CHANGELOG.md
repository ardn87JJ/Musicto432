# Journal des versions

## 0.3.0 — 2026-07-12

- Ajoute une file de conversion pour traiter plusieurs fichiers successivement.
- Ajoute l’arrêt réel d’une conversion, d’une file ou d’une analyse en cours.
- Rend l’action « Convertir un autre morceau » nettement plus visible.
- Distingue les analyses incertaines percussives, instables ou mélangeant plusieurs références.
- Ajoute un banc de calibration sur des morceaux réels de référence fournis légalement.
- Les installateurs futurs enregistrent automatiquement les versions appliquées dans Git.

## 0.2.0 — 2026-07-12

- Ajoute l’onglet « Vérifier l’accordage » pour les fichiers locaux et les liens YouTube.
- Estime la référence musicale, les écarts avec 432/440 Hz et un indice de confiance.
- Analyse plusieurs passages du morceau sans conserver le contenu après traitement.
- Ajoute des tests de référence automatiques à 432 Hz et 440 Hz.

## 0.1.2 — 2026-07-12

- Le suivi normal de la progression n’est plus compté dans la limite par minute.
- Empêche l’erreur « Trop de requêtes » pendant les conversions longues.

## 0.1.1 — 2026-07-12

- Corrige les permissions du stockage temporaire avec Podman/Docker Compose.
- Le healthcheck échoue désormais si l’API signale un stockage temporaire inaccessible.

## 0.1.0 — 2026-07-12

- Première version fonctionnelle du convertisseur 440 → 432 Hz.
- Import local MP3, WAV, FLAC, M4A, AAC et OGG.
- Sortie MP3 320 kbit/s, WAV PCM 24 bits ou FLAC.
- Progression réelle FFmpeg, écoute et téléchargement du résultat.
- Import YouTube optionnel avec confirmation des droits.
- Nettoyage automatique, limites, contrôles FFprobe et protections SSRF.
- Interface responsive claire/sombre et déploiement Docker Compose.
