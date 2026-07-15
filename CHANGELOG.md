# Journal des versions

## 0.7.0 — 2026-07-13

- Ajoute le Blueprint Render pour héberger publiquement FastAPI et FFmpeg.
- Ajoute le déploiement automatique du frontend sur GitHub Pages.
- Configure le chemin public `/Musicto432/` pour les scripts, le logo et le favicon.
- Permet de relier Pages au backend avec la variable GitHub `VITE_API_URL`.
- Limite le nettoyage des anciens service workers au seul périmètre MusicTo432.

## 0.6.1 — 2026-07-13

- Maintient le titre « Convertisseur musical 432 Hz » sur une ligne sur ordinateur.
- Conserve « 432 Hz » insécable lorsque le titre doit se replier sur mobile.
- Supprime l’installation PWA, son bouton, son manifeste et son service worker.
- Nettoie automatiquement les anciens service workers et caches MusicTo432.

## 0.6.0 — 2026-07-13

- Adopte une identité visuelle bleu nuit, cyan, violet et magenta assortie aux visuels MusicTo432.
- Intègre l’illustration 440 → 432 dans l’en-tête responsive.
- Remplace les icônes PWA, iPhone et favicon par l’icône officielle fournie.
- Renforce les contrastes, les états de focus et les effets lumineux sans réduire l’accessibilité.

## 0.5.0 — 2026-07-13

- Transforme le frontend en Progressive Web App installable.
- Ajoute une icône dédiée aux formats 180, 192 et 512 pixels.
- Ajoute le lancement plein écran `standalone` sur iPhone et ordinateur.
- Ajoute un bouton d’installation et des instructions adaptées à Safari iPhone.
- Met en cache uniquement le frontend ; les contenus audio et routes API restent exclus.
- Affiche un état hors ligne explicite lorsque le backend est inaccessible.

## 0.4.0 — 2026-07-13

- Ajoute le choix de la fréquence source et cible entre 400 et 480 Hz.
- Calcule le rapport de pitch côté serveur et refuse une source identique à la cible.
- Ajoute le téléchargement ZIP de tous les résultats d’une file.
- Ajoute la vérification YouTube avant traitement : titre, créateur, durée et miniature.
- Utilise le titre YouTube vérifié pour nommer le résultat.

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
