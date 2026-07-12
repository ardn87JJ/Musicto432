# Architecture

MusicTo432 est volontairement un petit monorepo monolithique : un frontend React statique et une API FastAPI. Il n’utilise ni base de données, ni file de messages, ni microservices.

## Flux d’un fichier local

1. Le navigateur envoie le fichier par formulaire multipart.
2. L’API crée un identifiant UUID aléatoire et un répertoire temporaire dédié.
3. La taille est contrôlée pendant l’écriture ; l’extension est vérifiée.
4. FFprobe confirme qu’une piste audio existe et contrôle durée, canaux et fréquence d’échantillonnage.
5. FFmpeg applique Rubber Band et publie sa progression réelle sur `pipe:1`.
6. FFprobe contrôle le fichier produit et compare sa durée et ses canaux à la source.
7. Les intermédiaires sont effacés ; seul le résultat reste disponible jusqu’à expiration.

## Composants backend

- `app/main.py` : routes, cycle de vie et middleware HTTP ;
- `services/media.py` : noms sûrs et analyse FFprobe ;
- `services/audio_converter.py` : commande FFmpeg, progression et contrôles de sortie ;
- `services/jobs.py` : état temporaire en mémoire, concurrence, expiration et suppression ;
- `services/youtube.py` : validation de l’URL et processus yt-dlp isolé ;
- `services/system.py` : capacités du runtime.

L’interface `JobManager` concentre l’état éphémère. Une future implémentation Redis peut reprendre les mêmes transitions d’état sans changer les routes publiques.

## Limites de la v0.1.0

- Un redémarrage du backend annule les tâches et états en mémoire.
- Plusieurs réplicas backend ne partagent pas leurs tâches ; il faut un routage collant ou un stockage d’état commun.
- La progression du téléchargement YouTube n’est pas affichée en pourcentage, car aucune valeur exacte stable n’est garantie ; l’étape réelle est affichée.
- Les tags usuels sont copiés avec `-map_metadata 0`. L’illustration intégrée n’est pas garantie pour tous les couples entrée/sortie.

