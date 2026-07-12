export const strings = {
  stages: {
    upload: 'Téléchargement vers le serveur',
    download: 'Récupération de la piste audio',
    preparation: 'Préparation et vérification',
    conversion: 'Conversion de la hauteur',
    finalization: 'Vérification du résultat',
    ready: 'Votre morceau est prêt',
  },
  formats: {
    mp3: { title: 'MP3', detail: '320 kbit/s · compatible partout' },
    wav: { title: 'WAV', detail: 'PCM 24 bits · non compressé' },
    flac: { title: 'FLAC', detail: 'Sans perte · fichier plus compact' },
  },
} as const

