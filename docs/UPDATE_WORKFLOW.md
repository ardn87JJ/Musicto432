# Workflow de mise à jour non destructif

La v0.1.0 est la création initiale complète. À partir de cette base, chaque évolution doit être livrée comme un patch versionné `MusicTo432_vX.X.X.patch`, accompagné d’un script d’application et de retour arrière.

## Règles de production d’un patch

1. Inspecter `git status`, `VERSION` et le dernier tag avant toute modification.
2. Ne jamais écraser les changements locaux de l’utilisateur.
3. Produire un diff depuis la version source exacte :

```bash
git diff --binary v0.1.0..HEAD > "$HOME/Téléchargements/MusicTo432_v0.2.0.patch"
```

4. Ajouter au script d’application : version source attendue, somme SHA-256 du patch, test `git apply --check`, sauvegarde datée hors du projet, application, tests et restauration en cas d’échec.
5. Refuser l’installation si le dépôt est sale, si la version ne correspond pas ou si un contrôle échoue, sauf procédure de résolution explicitement validée.
6. Ne remplacer un fichier entier que si cela est nécessaire et annoncé avant application.

## Contrôles minimaux du script futur

```bash
test "$(< VERSION)" = "0.1.0"
git status --porcelain --untracked-files=no | grep -q . && exit 1
sha256sum --check MusicTo432_v0.2.0.patch.sha256
git apply --check MusicTo432_v0.2.0.patch
```

Une sauvegarde complète ou un bundle Git est créé avant `git apply`. Si les tests échouent, le script conserve les journaux, restaure la sauvegarde et rend un code de sortie non nul.

