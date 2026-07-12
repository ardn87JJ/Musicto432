# MusicTo432

MusicTo432 est une application Web simple qui déplace relativement la hauteur d’un morceau supposé accordé sur **La = 440 Hz** vers **La = 432 Hz**, sans modifier son tempo ni sa durée. Le facteur appliqué est exactement `432 / 440` avec le filtre **Rubber Band** de FFmpeg.

## Démarrage rapide avec Docker

Prérequis : Git et Docker avec le plugin Compose.

```bash
git clone <URL_DU_DEPOT> MusicTo432
cd MusicTo432
cp .env.example .env
docker compose up --build
```

Ouvrir ensuite <http://localhost:8080>. L’API reste interne au réseau Docker et passe par le proxy du frontend.

Vérification :

```bash
curl http://localhost:8080/api/health
```

## Fonctions de la v0.1.0

- import local MP3, WAV, FLAC, M4A, AAC et OGG ;
- sortie MP3 320 kbit/s, WAV PCM 24 bits ou FLAC ;
- conversion `440 → 432` avec `rubberband=pitch=0.9818181818181818:tempo=1.0` ;
- progression calculée depuis la sortie `-progress` de FFmpeg ;
- contrôle du contenu, de la durée, du nombre de canaux et du résultat avec FFprobe ;
- écoute de l’original et du résultat ;
- téléchargement temporaire et suppression automatique ;
- import YouTube optionnel, isolé et désactivable ;
- analyse de l’accordage depuis un fichier ou un lien YouTube ;
- estimation de la référence en hertz, comparaison 432/440 et indice de confiance ;
- conversion successive de plusieurs fichiers avec résultats téléchargeables individuellement ;
- téléchargement groupé des résultats dans une archive ZIP ;
- choix de la fréquence source et cible entre 400 et 480 Hz ;
- prévisualisation d’un lien YouTube avant traitement ;
- frontend réutilisable hors ligne, sans mise en cache des fichiers audio ou de l’API ;
- arrêt immédiat et nettoyage d’une conversion ou d’une analyse ;
- interface française responsive, accessible au clavier, claire et sombre ;
- aucun compte, aucune base de données et aucun historique permanent.

## Développement sans Docker

Le FFmpeg local doit proposer le filtre Rubber Band :

```bash
ffmpeg -hide_banner -filters | grep rubberband
```

Backend :

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Frontend, dans un autre terminal :

```bash
cd frontend
npm ci
npm run dev
```

Ouvrir <http://localhost:5173>. Vite redirige `/api` vers `http://localhost:8000`.

## Tests

```bash
./scripts/doctor.sh
./scripts/test-all.sh
```

Le test audio génère lui-même une sinusoïde libre de droits à 440 Hz, la convertit et vérifie une fréquence proche de 432 Hz ainsi qu’une durée stable.

## API

| Méthode | Route | Rôle |
| --- | --- | --- |
| `GET` | `/api/health` | Vérification FFmpeg, FFprobe, Rubber Band et stockage temporaire |
| `GET` | `/api/capabilities` | Formats, limites et modules disponibles |
| `POST` | `/api/jobs/upload` | Création depuis un fichier multipart |
| `POST` | `/api/jobs/youtube` | Création depuis une URL YouTube autorisée |
| `POST` | `/api/youtube/inspect` | Vérification et métadonnées d’une vidéo YouTube |
| `POST` | `/api/jobs/batch-download` | Archive ZIP de plusieurs résultats terminés |
| `GET` | `/api/jobs/{job_id}` | Progression et état réel |
| `GET` | `/api/jobs/{job_id}/download` | Lecture ou téléchargement du résultat |
| `DELETE` | `/api/jobs/{job_id}` | Suppression immédiate |
| `POST` | `/api/analysis/upload` | Analyse d’un fichier audio |
| `POST` | `/api/analysis/youtube` | Analyse d’une piste YouTube autorisée |
| `GET` | `/api/analysis/{analysis_id}` | Progression et résultat de l’analyse |
| `DELETE` | `/api/analysis/{analysis_id}` | Suppression immédiate de l’analyse |

## Déploiement

GitHub peut héberger le dépôt et exécuter la CI. GitHub Pages peut éventuellement servir le build statique du frontend, mais **ne peut pas exécuter FastAPI, FFmpeg ou yt-dlp**. Le backend doit être déployé sur un service capable d’exécuter un conteneur et de fournir du stockage temporaire.

Voir [Architecture](docs/ARCHITECTURE.md), [Déploiement](docs/DEPLOYMENT.md), [Sécurité](docs/SECURITY.md), [Traitement audio](docs/AUDIO_PROCESSING.md), [Calibration](docs/CALIBRATION.md), [Droit et usage](docs/LEGAL_AND_USAGE.md) et [Mises à jour](docs/UPDATE_WORKFLOW.md).

## Limite essentielle

La conversion applique toujours un décalage relatif 440 → 432. L’onglet d’analyse fournit séparément une estimation statistique de l’accordage source : elle aide à choisir, mais ne constitue pas une mesure absolue ni une preuve de l’intention musicale d’origine.

## Licence

Le code du projet est publié sous licence MIT. FFmpeg, Rubber Band et yt-dlp restent soumis à leurs propres licences. Toute image Docker redistribuée doit conserver les avis et obligations des composants qu’elle contient.
