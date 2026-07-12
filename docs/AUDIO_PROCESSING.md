# Traitement audio 440 → 432 Hz

## Accordage et échantillonnage sont différents

« La = 440 Hz » décrit une référence musicale : la note La au-dessus du do central vibre à 440 cycles par seconde. Une fréquence d’échantillonnage comme 44 100 Hz ou 48 000 Hz décrit combien d’échantillons numériques sont enregistrés chaque seconde. Exporter à 43 200 Hz ne transforme donc pas un morceau en « musique 432 Hz ».

## Calcul appliqué

Le facteur de hauteur est :

```text
432 / 440 = 0.9818181818181818
```

La variation en cents vaut :

```text
1200 × log2(432 / 440) = −31.7666536334 cents
```

Toutes les fréquences musicales sont multipliées par ce rapport. Une composante à 440 Hz devient approximativement 432 Hz.

## Pourquoi Rubber Band

Changer simplement la fréquence d’échantillonnage ralentirait aussi la lecture et allongerait le morceau. Le pitch shifting de Rubber Band dissocie la hauteur du tempo. MusicTo432 exécute :

```text
rubberband=pitch=0.9818181818181818:tempo=1.0
```

La durée attendue reste donc quasiment identique. Une petite différence due à l’encodage et au remplissage des codecs est tolérée ; au-delà de 1 % ou 250 ms, le résultat est rejeté.

## Formats

- MP3 : nouvel encodage avec LAME à 320 kbit/s ;
- WAV : PCM signé 24 bits sans compression destructive ;
- FLAC : compression sans perte du signal traité.

Choisir WAV ou FLAC évite une nouvelle compression destructive du résultat, mais ne restaure pas les informations déjà perdues si la source est un MP3 ou un AAC.

## Limites

Le logiciel suppose que la source correspond à une référence 440 Hz. Il ne détecte ni la tonalité, ni l’accordage réel, ni les variations d’accordage entre instruments. Il applique uniformément le rapport à tout le mix. Les algorithmes de changement de hauteur peuvent créer de faibles artefacts, surtout sur des transitoires complexes ou après plusieurs réencodages.

## Estimation de l’accordage

L’onglet d’analyse extrait en mono plusieurs passages répartis dans le morceau, sans modifier le fichier original. Une transformée de Fourier repère les pics spectraux correspondant aux notes stables. Leur écart avec la grille tempérée basée sur La = 440 Hz est regroupé dans un histogramme circulaire de cents.

Le maximum de cet histogramme donne le décalage global probable. La référence est ensuite calculée par `440 × 2^(écart/1200)`. L’indice de confiance mesure la concentration des observations autour de ce maximum ; ce n’est pas une preuve absolue.

Les morceaux très percussifs, bruités, atonaux, utilisant plusieurs accordages, des glissandos permanents ou un tempérament non égal peuvent être classés « incertains ». L’analyse ne prétend pas identifier une intention artistique ni prouver qu’un morceau a été produit spécifiquement pour 432 Hz.
