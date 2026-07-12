# Installation de MusicTo432 comme application

MusicTo432 est une Progressive Web App. Son frontend peut être installé avec une icône, s’ouvrir sans barre d’adresse en mode autonome et réafficher son interface même lorsque le réseau est momentanément indisponible.

## Ordinateur

Avec l’application ouverte sur `http://localhost:8080`, utiliser le bouton « Installer » de MusicTo432 ou l’action d’installation proposée par Chrome/Chromium. `localhost` est considéré comme un contexte sécurisé pour le développement.

## iPhone et iPad

1. Ouvrir l’adresse HTTPS de MusicTo432 dans Safari.
2. Toucher le bouton Partager.
3. Choisir « Sur l’écran d’accueil ».
4. Valider le nom et l’icône.

L’application se lance ensuite depuis son icône en plein écran.

## HTTPS obligatoire sur iPhone

Les service workers sont autorisés uniquement dans un contexte sécurisé. `localhost` bénéficie d’une exception sur la machine qui héberge l’application, mais une adresse locale telle que `http://192.168.x.x:8080` n’est pas sécurisée pour l’iPhone. Pour bénéficier de l’installation complète et du cache hors ligne sur le téléphone, il faut exposer l’application avec un nom HTTPS et un certificat reconnu par l’iPhone.

## Ce qui fonctionne hors ligne

Le cache conserve uniquement l’interface HTML, CSS, JavaScript, le manifeste et les icônes. Les routes `/api/`, fichiers audio, résultats et contenus YouTube ne sont jamais placés dans le cache PWA. L’analyse et la conversion nécessitent donc toujours que le backend soit joignable.

À chaque nouvelle version, l’ancien cache du frontend est supprimé automatiquement. Le service worker utilise une stratégie réseau prioritaire pour les navigations et ne peut pas servir une ancienne API.
