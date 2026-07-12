#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

for command in python3 ffmpeg ffprobe node npm; do
  command -v "$command" >/dev/null || { echo "ERREUR : $command est absent." >&2; exit 1; }
done

ffmpeg -hide_banner -filters 2>/dev/null | grep -q rubberband || {
  echo "ERREUR : le filtre FFmpeg rubberband est absent." >&2
  exit 1
}

echo "Environnement compatible avec MusicTo432 $(< VERSION)."

