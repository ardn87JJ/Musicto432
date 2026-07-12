# Release v0.1.0

Première version MVP de MusicTo432.

## Validation avant publication

- [ ] `./scripts/doctor.sh`
- [ ] tests backend et test spectral 440 → 432
- [ ] tests, lint et build frontend
- [ ] construction Docker Compose
- [ ] conversion manuelle WAV, MP3, FLAC
- [ ] test sur Safari iPhone réel
- [ ] dépôt GitHub créé et distant configuré

## Création du tag

Après validation sur la machine cible :

```bash
git add -A
git commit -m "release: MusicTo432 v0.1.0"
git tag -a v0.1.0 -m "MusicTo432 v0.1.0"
git push origin main --follow-tags
```

