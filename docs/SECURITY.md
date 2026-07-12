# Sécurité

## Mesures présentes

- UUID aléatoires de 128 bits pour les tâches ;
- chemins et noms internes générés côté serveur ;
- normalisation du nom proposé pour le téléchargement ;
- liste fermée d’extensions et analyse réelle par FFprobe ;
- tailles et durées maximales configurables ;
- processus FFmpeg et yt-dlp créés avec une liste d’arguments, sans shell ;
- valeur de pitch et codecs choisis côté serveur ;
- répertoire isolé par tâche et nettoyage sur échec ;
- expiration et suppression manuelle ;
- sémaphore de conversion et limite simple de requêtes par IP ;
- CORS sur liste fermée et en-têtes de sécurité ;
- URL YouTube limitées à HTTPS et aux domaines prévus ;
- résolution DNS refusant les adresses locales, privées ou non globales ;
- refus des playlists, directs, comptes, cookies et contenus privés.

## Menaces et limites restantes

La limitation en mémoire convient à un MVP sur une seule instance. Pour une exposition publique importante, placer le service derrière un proxy ou pare-feu applicatif qui impose ses propres quotas, limites de connexions, taille et délais. L’adresse IP vue par l’application doit alors provenir uniquement d’un proxy de confiance.

`yt-dlp` suit le fonctionnement interne de YouTube et récupère les flux depuis des domaines de diffusion distincts. La validation initiale empêche une URL arbitraire ou locale ; pour un niveau SSRF strict face à toutes les redirections internes d’un outil tiers, exécuter le module dans un conteneur réseau séparé avec règles egress autorisant uniquement les services indispensables. Le désactiver reste la configuration la plus restrictive.

Le projet ne réalise pas d’analyse antivirus. Il ne réexpose que le résultat réencodé par FFmpeg, jamais l’entrée brute. Maintenir les images, FFmpeg, Python, FastAPI et yt-dlp à jour via des revues de dépendances.

## Journaux

Ne jamais ajouter aux journaux : contenu audio, URL complète avec paramètres sensibles, noms originaux complets, corps de requête ou chemin temporaire. Les identifiants de tâche peuvent être tronqués pour corrélation.

## Signaler une vulnérabilité

Ne pas ouvrir publiquement de ticket contenant une méthode d’exploitation ou des données utilisateur. Contacter en privé le mainteneur du dépôt et indiquer version, impact et reproduction minimale.

