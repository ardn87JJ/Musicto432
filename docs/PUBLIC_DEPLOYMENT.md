# Déploiement public : Render et GitHub Pages

L’interface statique est publiée sur GitHub Pages. L’API FastAPI, FFmpeg et les fichiers temporaires sont exécutés séparément sur Render.

## 1. Créer le backend Render

1. Connecter Render au dépôt GitHub `ardn87JJ/Musicto432`.
2. Créer un nouveau Blueprint depuis le fichier `render.yaml` à la racine.
3. Attendre que le service `musicto432-api` soit indiqué comme disponible.
4. Copier son URL HTTPS, par exemple `https://musicto432-api.onrender.com`.
5. Vérifier `https://URL_RENDER/api/health` : le statut doit être `ok`.

Le stockage reste temporaire. Un redémarrage du service supprime les traitements en cours, ce qui est cohérent avec la politique de confidentialité du projet.

## 2. Relier GitHub Pages à Render

Dans GitHub, ouvrir **Settings → Secrets and variables → Actions → Variables**, puis créer :

```text
Nom : VITE_API_URL
Valeur : https://URL_RENDER
```

Ne pas ajouter de `/` final.

## 3. Activer GitHub Pages

Dans **Settings → Pages**, choisir **GitHub Actions** comme source. Ouvrir ensuite **Actions → Deploy frontend to GitHub Pages** et relancer le workflow si le premier build a été créé avant la variable `VITE_API_URL`.

L’application sera publiée sur :

```text
https://ardn87jj.github.io/Musicto432/
```

## Limites d’un hébergement gratuit

Le serveur peut s’endormir et rendre la première requête lente. Les conversions consomment du CPU et les limites d’upload ou de durée imposées par l’hébergeur peuvent être inférieures aux limites configurées par l’application. L’import YouTube peut également être refusé par la plateforme depuis certaines adresses de centre de données ; l’import de fichiers locaux reste indépendant.
