# Déploiement

## Mode local

```bash
cp .env.example .env
docker compose up --build
```

L’application répond sur `http://localhost:8080`. Le stockage est un `tmpfs` éphémère. Ajuster sa taille et `MAX_CONCURRENT_JOBS` aux ressources de la machine.

## Production générique

Le frontend peut être servi par Nginx ou un hébergement statique. Le backend nécessite un hôte Docker avec :

- HTTPS au niveau du proxy public ;
- suffisamment de CPU et de mémoire pour FFmpeg ;
- un volume temporaire non persistant dimensionné ;
- une limite de corps HTTP égale à `MAX_UPLOAD_MB` ;
- un délai proxy supérieur au traitement le plus long ;
- un seul réplica pour cette version, sauf routage collant.

Si le frontend et l’API ont des domaines différents, construire le frontend avec :

```bash
VITE_API_URL=https://api.example.test npm run build
```

Puis définir précisément :

```dotenv
CORS_ORIGINS=https://app.example.test
```

Ne jamais mettre `*` en production. Les URL et secrets éventuels sont fournis par l’hébergeur, jamais committés.

## GitHub Pages

Pages peut servir `frontend/dist`, après configuration de `VITE_API_URL`, mais il ne peut pas exécuter FFmpeg. L’API doit être déployée séparément sur un service de conteneurs. Le workflow fourni vérifie le frontend, le backend et la construction Docker ; il ne publie rien automatiquement.

## Contrôles avant ouverture au public

1. `GET /api/health` doit répondre `status: ok` avec les quatre contrôles à `true`.
2. Tester un WAV court, puis un MP3 réel autorisé.
3. Vérifier l’expiration et la suppression immédiate.
4. Adapter le débit par IP et la concurrence.
5. Si YouTube n’est pas souhaité, définir `YOUTUBE_ENABLED=false`.
6. Surveiller CPU, espace temporaire, erreurs FFmpeg et statuts HTTP sans journaliser les contenus.

